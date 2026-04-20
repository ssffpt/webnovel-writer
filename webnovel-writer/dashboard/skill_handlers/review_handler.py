"""ReviewSkillHandler — 8-step review skill (steps 1-3 implemented)."""
from __future__ import annotations

import asyncio
import json
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
        # step_4 ~ step_8 in future tasks
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        if step.step_id == "step_4":
            if not data.get("confirmed", False):
                return "请确认审查报告"
            return None
        if step.step_id == "step_7":
            decisions = data.get("decisions", [])
            if not decisions:
                return "请对关键问题做出决策"
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
