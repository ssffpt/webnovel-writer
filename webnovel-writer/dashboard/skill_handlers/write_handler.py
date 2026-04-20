"""WriteSkillHandler — 6-step chapter writing workflow."""
from __future__ import annotations

import asyncio

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
        if step.step_id == "step_5":
            return {"message": "Data Agent（待实现）"}
        if step.step_id == "step_6":
            return {"message": "Git 备份（待实现）"}
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

        # TODO: actual AI call
        # Fallback mode
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

        # TODO: actual AI call
        # Fallback mode: no modification
        adapted_text = draft_text

        context["adapted_text"] = adapted_text

        # Generate diff (simplified: mark whether there were changes)
        has_changes = adapted_text != draft_text

        return {
            "adapted_text": adapted_text,
            "has_changes": has_changes,
            "changes_summary": "风格适配完成" if has_changes else "无需调整（降级模式）",
            "instruction": "请确认风格适配结果",
        }

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
