"""WriteSkillHandler — 6-step chapter writing workflow."""
from __future__ import annotations

import asyncio
import json

from pathlib import Path

import aiohttp

from ..script_adapter import ScriptAdapter
from ..skill_runner import SkillHandler
from ..skill_models import StepDefinition, StepState


class WriteSkillHandler(SkillHandler):
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """Return step list for the given mode.

        mode:
            "standard" (default) — all steps
            "fast" — skip Step 2B (style adaptation)
            "minimal" — skip Step 2B, Step 3 core 3-item review only
        """
        mode = mode or "standard"

        steps = [
            StepDefinition(id="step_1", name="Context Agent", interaction="auto"),
            StepDefinition(id="step_2a", name="正文起草", interaction="confirm"),
            StepDefinition(
                id="step_2b",
                name="风格适配",
                interaction="confirm",
                skippable=(mode in ("fast", "minimal")),
            ),
            StepDefinition(id="step_3", name="六维审查", interaction="auto"),
            StepDefinition(id="step_4", name="润色", interaction="confirm"),
            StepDefinition(id="step_5", name="Data Agent", interaction="auto"),
            StepDefinition(id="step_6", name="Git 备份", interaction="auto"),
        ]

        return steps

    async def execute_step(self, step: StepState, context: dict) -> dict:
        """Execute an auto step. Full implementations come in later tasks."""
        if step.step_id == "step_1":
            from .context_builder import ContextBuilder
            builder = ContextBuilder(context)
            return await builder.build()
        if step.step_id == "step_2a":
            return await self._draft_chapter(context)
        if step.step_id == "step_2b":
            return await self._style_adapt(context)
        if step.step_id == "step_3":
            return await self._run_review(step, context)
        if step.step_id == "step_4":
            return await self._polish(step, context)
        if step.step_id == "step_5":
            from .data_agent import DataAgent
            agent = DataAgent(context)
            return await agent.run()
        if step.step_id == "step_6":
            return await self._git_backup(context)
        return {}

    async def _draft_chapter(self, context: dict) -> dict:
        """Call AI API to generate chapter draft.

        Input: execution_pack (with outline, settings, constraints)
        Output: 2000-2500 word draft text

        Fallback mode (no AI API): returns template placeholder text.
        """
        execution_pack = context.get("execution_pack", {})
        task_brief = context.get("task_brief", {})
        chapter_num = context.get("chapter_num", 1)
        project_root = context.get("project_root", ".")

        draft = await self._call_llm_for_draft(
            chapter_num, execution_pack, task_brief, project_root
        )
        if draft is None:
            draft = self._fallback_draft(chapter_num, task_brief)

        context["draft_text"] = draft
        context["draft_word_count"] = len(draft)

        return {
            "draft_text": draft,
            "word_count": len(draft),
            "instruction": "请预览草稿，确认或修改后继续",
        }

    def _fallback_draft(self, chapter_num: int, task_brief: dict) -> str:
        """Fallback template draft when AI is unavailable."""
        outline = task_brief.get("chapter_outline", "")
        return (
            f"# 第{chapter_num}章\n\n"
            f"[AI 草稿占位 — 基于大纲生成]\n\n"
            f"大纲摘要：{outline[:200] if outline else '无大纲'}\n\n"
            f"{'占位正文。' * 100}\n"
        )

    async def _style_adapt(self, context: dict) -> dict:
        """Call AI API for style adaptation.

        Goals: eliminate three AI voices:
        1. Template voice — fixed patterns, overuse of "然而"/"不禁"
        2. Exposition voice — encyclopedic explanation of settings
        3. Mechanical voice — lack of emotion, monotonous rhythm

        Input: draft_text (from Step 2A)
        Output: style-adapted text + diff markers

        Fallback mode: returns original text unchanged.
        """
        draft_text = context.get("draft_text", "")
        task_brief = context.get("task_brief", {})
        style_reference = task_brief.get("style_reference", "")
        project_root = context.get("project_root", ".")

        adapted_text = await self._call_llm_for_style_adapt(
            draft_text, style_reference, project_root
        )
        if adapted_text is None:
            adapted_text = draft_text

        context["adapted_text"] = adapted_text

        has_changes = adapted_text != draft_text

        return {
            "adapted_text": adapted_text,
            "has_changes": has_changes,
            "changes_summary": "风格适配完成" if has_changes else "无需调整（降级模式）",
            "instruction": "请确认风格适配结果",
        }

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _get_llm_config(self, project_root: str) -> dict:
        """Read LLM config from RAG config (reuses API key / base URL)."""
        from ..rag_config import RAGConfig

        cfg = RAGConfig(project_root)
        api_key = cfg.get("RAG_EMBEDDING_API_KEY") or cfg.get("OPENAI_API_KEY", "")
        base_url = cfg.get("RAG_EMBEDDING_BASE_URL", "https://api.openai.com/v1")
        model = cfg.get("RAG_LLM_MODEL", "gpt-4o-mini")
        return {
            "api_key": api_key,
            "base_url": base_url.rstrip("/"),
            "model": model,
        }

    async def _call_llm(self, messages: list[dict], project_root: str, temperature: float = 0.8) -> str | None:
        """Call OpenAI-compatible chat completions API."""
        llm_cfg = self._get_llm_config(project_root)
        api_key = llm_cfg["api_key"]
        if not api_key:
            return None

        url = f"{llm_cfg['base_url']}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": llm_cfg["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    choice = data.get("choices", [{}])[0]
                    return choice.get("message", {}).get("content", "")
        except Exception:
            return None

    async def _call_llm_for_draft(
        self, chapter_num: int, execution_pack: dict, task_brief: dict, project_root: str
    ) -> str | None:
        """Build prompt and call LLM to generate chapter draft."""
        outline = task_brief.get("chapter_outline", "")[:800]
        prev_summaries = task_brief.get("previous_summaries", [])[:3]
        settings = task_brief.get("relevant_settings", "")[:1200]
        foreshadowing = task_brief.get("pending_foreshadowing", [])[:5]
        constraints = task_brief.get("core_constraints", "")[:800]
        style_ref = task_brief.get("style_reference", "")[:600]

        system_msg = (
            "你是一位专业中文网络小说写手。请严格根据提供的大纲、设定和约束创作章节正文。"
            "要求：\n"
            "1. 输出纯正文，不要添加章节标题、作者备注或总结\n"
            "2. 字数 2000-2500 字\n"
            "3. 语言流畅自然，避免模板化表达（如过度使用“然而”“不禁”“仿佛”）\n"
            "4. 保持人物言行一致，伏笔需自然回收\n"
            "5. 节奏有张有弛，适当加入对话和动作描写"
        )

        user_parts = []
        user_parts.append(f"## 章节大纲\n{outline if outline else '（无大纲）'}")
        if prev_summaries:
            user_parts.append(f"## 前文摘要\n" + "\n".join(f"- {s}" for s in prev_summaries))
        if settings:
            user_parts.append(f"## 相关设定\n{settings}")
        if foreshadowing:
            fs_text = "\n".join(
                f"- {f.get('text', f) if isinstance(f, dict) else f}" for f in foreshadowing
            )
            user_parts.append(f"## 待回收伏笔\n{fs_text}")
        if constraints:
            user_parts.append(f"## 写作约束\n{constraints}")
        if style_ref:
            user_parts.append(f"## 风格参考\n{style_ref}")
        user_parts.append(f"\n请创作第 {chapter_num} 章正文。")

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

        return await self._call_llm(messages, project_root, temperature=0.8)

    async def _call_llm_for_style_adapt(
        self, draft_text: str, style_reference: str, project_root: str
    ) -> str | None:
        """Build prompt and call LLM for style adaptation."""
        system_msg = (
            "你是一位资深中文小说编辑。请对提供的章节草稿进行风格适配，消除以下三种 AI 腔调：\n"
            "1. 模板腔 — 固定句式、过度使用“然而”“不禁”“不由得”\n"
            "2. 说明腔 — 像百科一样解释设定，缺乏沉浸感\n"
            "3. 机械腔 — 情绪扁平、节奏单调\n"
            "要求：保持原意和情节不变，仅优化表达。输出纯正文，不要添加标题或备注。"
        )

        user_parts = [f"## 草稿\n{draft_text}"]
        if style_reference:
            user_parts.append(f"## 风格参考\n{style_reference[:800]}")
        user_parts.append("\n请对草稿进行风格适配优化。")

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "\n\n".join(user_parts)},
        ]

        return await self._call_llm(messages, project_root, temperature=0.7)

    async def _run_review(self, step: StepState, context: dict) -> dict:
        """并行执行六维审查。"""
        from .review_checkers import (
            HookDensityChecker,
            SettingConsistencyChecker,
            RhythmRatioChecker,
            CharacterOOCChecker,
            NarrativeCoherenceChecker,
            ReadabilityChecker,
        )

        text = context.get("adapted_text") or context.get("draft_text", "")
        task_brief = context.get("task_brief", {})
        contract = context.get("context_contract", {})
        mode = context.get("mode", "standard")

        if mode == "minimal":
            checkers = [
                SettingConsistencyChecker(text, task_brief, contract),
                CharacterOOCChecker(text, task_brief, contract),
                NarrativeCoherenceChecker(text, task_brief, contract),
            ]
        else:
            checkers = [
                HookDensityChecker(text, task_brief, contract),
                SettingConsistencyChecker(text, task_brief, contract),
                RhythmRatioChecker(text, task_brief, contract),
                CharacterOOCChecker(text, task_brief, contract),
                NarrativeCoherenceChecker(text, task_brief, contract),
                ReadabilityChecker(text, task_brief, contract),
            ]

        results = await asyncio.gather(
            *[checker.check() for checker in checkers],
            return_exceptions=True,
        )

        review_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                review_results.append({
                    "dimension": checkers[i].dimension,
                    "score": 0,
                    "passed": False,
                    "issues": [{"severity": "error", "message": str(result)}],
                })
            else:
                review_results.append(result)

        total_score = sum(r["score"] for r in review_results) / len(review_results) if review_results else 0

        all_issues = []
        for r in review_results:
            for issue in r.get("issues", []):
                issue["dimension"] = r["dimension"]
                all_issues.append(issue)

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

        context["review_results"] = review_results
        context["review_issues"] = all_issues
        context["review_score"] = total_score

        return {
            "review_results": review_results,
            "total_score": round(total_score, 1),
            "issues_count": len(all_issues),
            "critical_count": sum(1 for i in all_issues if i.get("severity") == "critical"),
            "instruction": f"审查完成，总分 {total_score:.1f}/10，{len(all_issues)} 个问题",
        }

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """Validate user input for confirm steps."""
        if step.step_id == "step_2a":
            return self._validate_draft_confirm(data)
        if step.step_id == "step_2b":
            return self._validate_style_confirm(data)
        if step.step_id == "step_4":
            return self._validate_polish_confirm(data)
        return None

    def _validate_draft_confirm(self, data: dict) -> str | None:
        """Step 2A confirm: user confirms draft or submits edited text."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            edited_text = data.get("edited_text", "")
            if not edited_text:
                return "请确认草稿或提交修改后的文本"
        return None

    def _validate_style_confirm(self, data: dict) -> str | None:
        """Step 2B confirm: user confirms style adaptation result."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            feedback = data.get("feedback", "")
            if not feedback:
                return "请确认风格适配结果或提出修改意见"
        return None

    def _validate_polish_confirm(self, data: dict) -> str | None:
        """Step 4 confirm: user confirms polish result."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            edited_text = data.get("edited_text", "")
            if not edited_text:
                return "请确认润色结果或提交修改后的文本"
        return None

    async def _polish(self, step: StepState, context: dict) -> dict:
        """Anti-AI 终检：检测并消除 AI 常见痕迹词汇。"""
        current_text = context.get("adapted_text") or context.get("draft_text", "")
        issues = context.get("review_issues", [])

        critical_issues = [i for i in issues if i.get("severity") == "critical"]
        high_issues = [i for i in issues if i.get("severity") == "high"]
        other_issues = [i for i in issues if i.get("severity") in ("medium", "low")]

        medium_issues = [i for i in issues if i.get("severity") == "medium"]
        low_issues = [i for i in issues if i.get("severity") == "low"]

        # 降级模式：执行 Anti-AI 终检的简单规则替换
        polished_text = self._anti_ai_check(current_text)

        fix_report = {
            "critical_count": len(critical_issues),
            "high_count": len(high_issues),
            "medium_count": len(medium_issues),
            "low_count": len(low_issues),
            "anti_ai_fixes": self._count_anti_ai_fixes(current_text, polished_text),
        }

        context["polished_text"] = polished_text
        context["fix_report"] = fix_report

        return {
            "polished_text": polished_text,
            "original_text": current_text,
            "fix_report": fix_report,
            "word_count": len(polished_text),
            "has_changes": polished_text != current_text,
            "instruction": "请确认润色结果，或手动修改后提交",
        }

    def _anti_ai_check(self, text: str) -> str:
        """Anti-AI 终检：替换 AI 常见痕迹词汇。"""
        import re

        ai_words = {
            "不禁": 2,
            "竟然": 3,
            "然而": 2,
            "居然": 3,
            "仿佛": 3,
            "宛如": 2,
            "不由得": 2,
        }

        result = text
        for word, max_count in ai_words.items():
            count = result.count(word)
            if count > max_count:
                parts = result.split(word)
                new_parts = []
                kept = 0
                for i, part in enumerate(parts[:-1]):
                    new_parts.append(part)
                    if kept < max_count:
                        new_parts.append(word)
                        kept += 1
                new_parts.append(parts[-1])
                result = "".join(new_parts)

        return result

    def _count_anti_ai_fixes(self, original: str, polished: str) -> int:
        """统计 Anti-AI 修复的数量。"""
        if original == polished:
            return 0
        diff_chars = abs(len(original) - len(polished))
        for i in range(min(len(original), len(polished))):
            if original[i] != polished[i]:
                diff_chars += 1
        return max(1, diff_chars // 10)

    async def _git_backup(self, context: dict) -> dict:
        """Git 自动提交（可选）。"""
        project_root = Path(context.get("project_root", "."))
        chapter_num = context.get("chapter_num", 1)

        config_path = project_root / ".webnovel" / "config.json"
        auto_commit = False
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                auto_commit = config.get("auto_git_commit", False)
            except json.JSONDecodeError:
                pass

        if not auto_commit:
            return {
                "skipped": True,
                "reason": "auto_git_commit 未开启",
                "instruction": "Git 备份已跳过（未开启自动提交）",
            }

        adapter = ScriptAdapter(project_root=str(project_root))
        message = f"[webnovel] 第{chapter_num}章（write Step 6）"
        result = await adapter.git_commit(message)

        if not result.get("success"):
            return {
                "skipped": False,
                "success": False,
                "error": result.get("error", ""),
                "instruction": f"Git 提交失败（不影响流程）：{result.get('error', '')}",
            }

        return {
            "skipped": False,
            "success": True,
            "commit_hash": result.get("commit_hash"),
            "instruction": f"Git 提交成功：{result.get('commit_hash', '')}",
        }
