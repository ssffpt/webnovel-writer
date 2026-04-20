"""ReviewSkillHandler — 8-step review skill (steps 1-3 implemented)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from dashboard.skill_models import StepDefinition, StepState
from dashboard.skill_runner import SkillHandler


class ReviewSkillHandler(SkillHandler):
    """8-step review skill.

    Step definitions:
    - step_1: 加载参考           (auto)
    - step_2: 加载项目状态        (auto)
    - step_3: 并行审查           (auto)
    - step_4: 生成审查报告        (confirm)
    - step_5: 保存审查指标        (auto)
    - step_6: 写回审查记录        (auto)
    - step_7: 处理关键问题        (confirm)
    - step_8: 收尾               (auto)
    """

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="加载参考",        interaction="auto"),
            StepDefinition(id="step_2", name="加载项目状态",    interaction="auto"),
            StepDefinition(id="step_3", name="并行审查",        interaction="auto"),
            StepDefinition(id="step_4", name="生成审查报告",    interaction="confirm"),
            StepDefinition(id="step_5", name="保存审查指标",    interaction="auto"),
            StepDefinition(id="step_6", name="写回审查记录",    interaction="auto"),
            StepDefinition(id="step_7", name="处理关键问题",    interaction="confirm"),
            StepDefinition(id="step_8", name="收尾",            interaction="auto"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        if step.step_id == "step_1":
            return await self._load_references(context)
        if step.step_id == "step_2":
            return await self._load_project_state(context)
        if step.step_id == "step_3":
            return await self._run_parallel_review(step, context)
        if step.step_id == "step_4":
            return await self._generate_report(context)
        if step.step_id == "step_5":
            return await self._save_metrics(context)
        if step.step_id == "step_6":
            return await self._writeback_state(context)
        if step.step_id == "step_7":
            # Transfer decisions from step object to context (stored by validate_input)
            if hasattr(step, "_critical_decisions"):
                context["_critical_decisions"] = step._critical_decisions
            return await self._handle_critical_issues(context)
        if step.step_id == "step_8":
            return await self._finalize(context)
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        if step.step_id == "step_4":
            if not data.get("confirmed", False):
                return "请确认审查报告"
            return None
        if step.step_id == "step_7":
            decisions = data.get("decisions", [])
            if not decisions:
                return "请对每个关键问题做出决策"
            valid_options = {"auto_fix", "ignore", "manual"}
            for d in decisions:
                if d.get("option_id") not in valid_options:
                    return f"无效的修复方案：{d.get('option_id')}"
            # Store decisions in step object for later retrieval by execute_step
            step._critical_decisions = decisions
            return None
        return None

    # ------------------------------------------------------------------
    # Step 1: Load references
    # ------------------------------------------------------------------

    async def _load_references(self, context: dict) -> dict:
        """Load review reference material: core-constraints, creativity package, style guide."""
        project_root = Path(context.get("project_root", "."))

        # 1. core-constraints
        constraints_path = project_root / ".webnovel" / "core-constraints.md"
        constraints = ""
        if constraints_path.exists():
            constraints = constraints_path.read_text(encoding="utf-8")

        # 2. creativity package from idea_bank
        idea_bank_path = project_root / ".webnovel" / "idea_bank.json"
        creativity_constraints: list[dict] = []
        if idea_bank_path.exists():
            try:
                idea_bank = json.loads(idea_bank_path.read_text(encoding="utf-8"))
                pkg = idea_bank.get("creativity_package", {})
                creativity_constraints = pkg.get("constraints", [])
            except json.JSONDecodeError:
                pass

        # 3. 总纲 (outline as consistency reference)
        outline_path = project_root / "大纲" / "总纲.md"
        outline = ""
        if outline_path.exists():
            outline = outline_path.read_text(encoding="utf-8")

        # 4. 设定集
        setting_dir = project_root / "设定集"
        settings: dict[str, str] = {}
        if setting_dir.exists():
            for f in setting_dir.glob("*.md"):
                settings[f.stem] = f.read_text(encoding="utf-8")

        context["references"] = {
            "core_constraints": constraints,
            "creativity_constraints": creativity_constraints,
            "outline": outline,
            "settings": settings,
        }

        return {
            "loaded": True,
            "has_constraints": bool(constraints),
            "creativity_constraints_count": len(creativity_constraints),
            "settings_count": len(settings),
            "instruction": "参考资料加载完成",
        }

    # ------------------------------------------------------------------
    # Step 2: Load project state
    # ------------------------------------------------------------------

    async def _load_project_state(self, context: dict) -> dict:
        """Load state.json and target chapter body text."""
        project_root = Path(context.get("project_root", "."))
        chapter_start = int(context.get("chapter_start", 1))
        chapter_end = int(context.get("chapter_end", chapter_start))

        # 1. state.json
        state_path = project_root / ".webnovel" / "state.json"
        state: dict = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass
        context["project_state"] = state

        # 2. Load target chapter body text
        chapters: dict[int, str] = {}
        chapter_dir = project_root / "正文"
        for ch_num in range(chapter_start, chapter_end + 1):
            ch_path = chapter_dir / f"第{ch_num}章.md"
            if ch_path.exists():
                chapters[ch_num] = ch_path.read_text(encoding="utf-8")

        context["review_chapters"] = chapters

        # 3. Load chapter outlines
        chapter_outlines: dict[int, dict] = {}
        outline_dir = project_root / "大纲"
        if outline_dir.exists():
            for vol_dir in outline_dir.iterdir():
                if vol_dir.is_dir():
                    for ch_num in range(chapter_start, chapter_end + 1):
                        ch_file = vol_dir / f"第{ch_num}章.json"
                        if ch_file.exists():
                            try:
                                chapter_outlines[ch_num] = json.loads(
                                    ch_file.read_text(encoding="utf-8")
                                )
                            except json.JSONDecodeError:
                                pass
        context["chapter_outlines"] = chapter_outlines

        return {
            "chapters_loaded": len(chapters),
            "chapters_missing": [
                ch for ch in range(chapter_start, chapter_end + 1)
                if ch not in chapters
            ],
            "has_outlines": len(chapter_outlines) > 0,
            "instruction": f"已加载 {len(chapters)} 章正文",
        }

    # ------------------------------------------------------------------
    # Step 3: Parallel review
    # ------------------------------------------------------------------

    async def _run_parallel_review(self, step: StepState, context: dict) -> dict:
        """对每章执行六维并行审查。

        多章审查时，逐章执行（每章内部 6 维并行）。
        通过 step.progress 推送整体进度。
        """
        from .review_checkers import (
            HookDensityChecker,
            SettingConsistencyChecker,
            RhythmRatioChecker,
            CharacterOOCChecker,
            NarrativeCoherenceChecker,
            ReadabilityChecker,
        )

        chapters = context.get("review_chapters", {})
        references = context.get("references", {})
        chapter_outlines = context.get("chapter_outlines", {})

        task_brief = {
            "relevant_settings": "\n".join(references.get("settings", {}).values()),
            "chapter_outline": "",
            "previous_summaries": [],
            "pending_foreshadowing": [],
            "character_states": {},
            "core_constraints": references.get("core_constraints", ""),
            "style_reference": "",
        }

        contract = {
            "setting_constraints": self._extract_constraints_from_references(references),
            "foreshadowing_obligations": [],
            "timeline_anchor": "",
            "character_boundaries": {},
        }

        all_chapter_results = {}
        chapter_nums = sorted(chapters.keys())
        total = len(chapter_nums)

        for i, ch_num in enumerate(chapter_nums):
            text = chapters[ch_num]

            ch_outline = chapter_outlines.get(ch_num, {})
            task_brief["chapter_outline"] = json.dumps(ch_outline, ensure_ascii=False) if ch_outline else ""

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

            chapter_results = []
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    chapter_results.append({
                        "dimension": checkers[j].dimension,
                        "score": 0,
                        "passed": False,
                        "issues": [{"severity": "error", "message": str(result)}],
                    })
                else:
                    chapter_results.append(result)

            all_chapter_results[ch_num] = chapter_results
            # Note: step.progress mutation is lost after this method returns.
            # Progress is tracked via SSE in SkillRunner, not via step object mutation.
            step.progress = (i + 1) / total

        context["all_chapter_results"] = all_chapter_results
        summary = self._summarize_review(all_chapter_results)
        context["review_summary"] = summary

        return {
            "all_chapter_results": all_chapter_results,
            "summary": summary,
            "instruction": f"审查完成：{total} 章，平均分 {summary['avg_score']:.1f}/10",
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _summarize_review(self, all_results: dict) -> dict:
        """汇总多章审查结果。"""
        all_scores = []
        all_issues = []
        dimension_scores = {}

        for ch_num, results in all_results.items():
            for r in results:
                dim = r["dimension"]
                all_scores.append(r["score"])
                dimension_scores.setdefault(dim, []).append(r["score"])
                for issue in r.get("issues", []):
                    issue["chapter"] = ch_num
                    issue["dimension"] = dim
                    all_issues.append(issue)

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "error": 0}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))

        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        dimension_avg = {
            dim: sum(scores) / len(scores)
            for dim, scores in dimension_scores.items()
        }

        return {
            "avg_score": round(avg_score, 1),
            "dimension_avg": {k: round(v, 1) for k, v in dimension_avg.items()},
            "total_issues": len(all_issues),
            "critical_issues": [i for i in all_issues if i.get("severity") == "critical"],
            "high_issues": [i for i in all_issues if i.get("severity") == "high"],
            "all_issues": all_issues,
        }

    def _extract_constraints_from_references(self, references: dict) -> list[str]:
        """从参考资料中提取硬约束。"""
        constraints = []
        core = references.get("core_constraints", "")
        for line in core.split("\n"):
            line = line.strip()
            if line.startswith("- "):
                constraints.append(line[2:])

        for c in references.get("creativity_constraints", []):
            constraints.append(c.get("content", ""))

        return constraints

    # ------------------------------------------------------------------
    # Step 4: Generate review report
    # ------------------------------------------------------------------

    async def _generate_report(self, context: dict) -> dict:
        """生成结构化审查报告。"""
        summary = context.get("review_summary", {})
        all_results = context.get("all_chapter_results", {})

        report = {
            "overall": {
                "avg_score": summary.get("avg_score", 0),
                "dimension_scores": summary.get("dimension_avg", {}),
                "total_issues": summary.get("total_issues", 0),
                "verdict": self._get_verdict(summary.get("avg_score", 0)),
            },
            "chapters": {},
            "priority_fixes": [],
            "suggestions": [],
        }

        for ch_num, results in all_results.items():
            ch_score = sum(r["score"] for r in results) / len(results) if results else 0
            report["chapters"][ch_num] = {
                "score": round(ch_score, 1),
                "dimensions": {r["dimension"]: r["score"] for r in results},
                "issues_count": sum(len(r.get("issues", [])) for r in results),
            }

        critical = summary.get("critical_issues", [])
        high = summary.get("high_issues", [])
        report["priority_fixes"] = critical + high
        report["suggestions"] = self._generate_suggestions(summary)

        context["review_report"] = report

        return {
            "report": report,
            "instruction": "请确认审查报告",
        }

    def _get_verdict(self, avg_score: float) -> str:
        if avg_score >= 8.5:
            return "优秀"
        elif avg_score >= 7.0:
            return "良好"
        elif avg_score >= 6.0:
            return "合格"
        else:
            return "需要修改"

    def _generate_suggestions(self, summary: dict) -> list[str]:
        suggestions = []
        dim_avg = summary.get("dimension_avg", {})

        if dim_avg.get("爽点密度", 10) < 6:
            suggestions.append("增加情节转折和情绪波动，提升爽点密度")
        if dim_avg.get("设定一致性", 10) < 6:
            suggestions.append("检查设定矛盾，确保力量体系和世界观一致")
        if dim_avg.get("节奏比例", 10) < 6:
            suggestions.append("调整对话/描写/动作比例，避免大段纯叙述")
        if dim_avg.get("人物OOC", 10) < 6:
            suggestions.append("检查角色行为是否符合已建立的性格特征")
        if dim_avg.get("叙事连贯性", 10) < 6:
            suggestions.append("检查前后文逻辑，消除跳跃和矛盾")
        if dim_avg.get("追读力", 10) < 6:
            suggestions.append("强化章末钩子，增加悬念和期待感")

        return suggestions

    # ------------------------------------------------------------------
    # Step 5: Save metrics to index.db
    # ------------------------------------------------------------------

    async def _save_metrics(self, context: dict) -> dict:
        """Step 5: 保存审查指标到 index.db。"""
        from .review_storage import ReviewStorage

        storage = ReviewStorage(context.get("project_root", "."))
        result = storage.save_metrics(
            context.get("all_chapter_results", {}),
            context.get("review_summary", {}),
        )

        return {
            "metrics_saved": True,
            "session_id": result.get("session_id"),
            "instruction": "审查指标已保存",
        }

    # ------------------------------------------------------------------
    # Step 6: Writeback state.json
    # ------------------------------------------------------------------

    async def _writeback_state(self, context: dict) -> dict:
        """Step 6: 写回审查记录到 state.json。"""
        from .review_storage import ReviewStorage

        storage = ReviewStorage(context.get("project_root", "."))
        result = storage.writeback_state(context.get("all_chapter_results", {}))

        return {
            "state_updated": True,
            "chapters_updated": result.get("chapters_updated", []),
            "instruction": "审查记录已写回 state.json",
        }

    # ------------------------------------------------------------------
    # Step 7: Handle critical issues
    # ------------------------------------------------------------------

    async def _handle_critical_issues(self, context: dict) -> dict:
        """处理 critical 问题。"""
        summary = context.get("review_summary", {})
        critical_issues = summary.get("critical_issues", [])

        if not critical_issues:
            return {
                "has_critical": False,
                "auto_resolved": True,
                "instruction": "无关键问题，自动通过",
            }

        issues_with_options = []
        for issue in critical_issues:
            options = self._generate_fix_options(issue)
            issues_with_options.append({
                "issue": issue,
                "options": options,
            })

        context["critical_issues_with_options"] = issues_with_options

        return {
            "has_critical": True,
            "auto_resolved": False,
            "requires_input": True,
            "issues_with_options": issues_with_options,
            "instruction": f"发现 {len(critical_issues)} 个关键问题，请选择修复方案",
        }

    def _generate_fix_options(self, issue: dict) -> list[dict]:
        return [
            {
                "id": "auto_fix",
                "label": "AI 自动修复",
                "description": f"自动修改相关段落以解决：{issue.get('message', '')}",
            },
            {
                "id": "ignore",
                "label": "标记为可接受",
                "description": "确认此问题不影响阅读体验，标记为已知",
            },
            {
                "id": "manual",
                "label": "稍后手动修复",
                "description": "记录到待办列表，稍后手动处理",
            },
        ]

    # ------------------------------------------------------------------
    # Step 8: Finalize
    # ------------------------------------------------------------------

    async def _finalize(self, context: dict) -> dict:
        """收尾：保存审查报告文件 + 处理用户决策。"""
        project_root = Path(context.get("project_root", "."))
        report = context.get("review_report", {})
        chapter_start = context.get("chapter_start", 1)
        chapter_end = context.get("chapter_end", chapter_start)

        # 1. 保存审查报告到文件
        report_dir = project_root / ".webnovel" / "审查报告"
        report_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"review_{chapter_start}-{chapter_end}_{timestamp}.json"
        report_path = report_dir / report_filename
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 2. 处理 critical 问题决策
        decisions = context.get("_critical_decisions", [])
        manual_todos = []
        for d in decisions:
            if d.get("option_id") == "manual":
                manual_todos.append(d.get("issue", {}))

        # 3. 如果有"稍后手动修复"的问题，写入待办
        if manual_todos:
            todo_path = project_root / ".webnovel" / "review_todos.json"
            existing_todos = []
            if todo_path.exists():
                try:
                    existing_todos = json.loads(todo_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            existing_todos.extend(manual_todos)
            todo_path.write_text(
                json.dumps(existing_todos, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return {
            "report_saved": str(report_path),
            "manual_todos": len(manual_todos),
            "instruction": f"审查完成，报告已保存至 {report_filename}",
        }
