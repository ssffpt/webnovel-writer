"""PlanValidator — 7-item validation checks for volume planning output."""

from __future__ import annotations


class PlanValidator:
    """Runs 7 validation checks on the plan context."""

    def __init__(self, context: dict):
        self.context = context
        self.chapter_outlines = context.get("chapter_outlines", [])
        self.beat_sheet = context.get("beat_sheet", [])
        self.timeline = context.get("timeline", [])
        self.skeleton = context.get("volume_skeleton", {})
        self.outline = context.get("outline", "")
        self.idea_bank = context.get("idea_bank", {})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all_checks(self) -> list[dict]:
        """Execute all 7 validation checks, return a list of result dicts."""
        return [
            self.check_hook_density(),
            self.check_strand_ratio(),
            self.check_outline_consistency(),
            self.check_constraint_frequency(),
            self.check_chapter_completeness(),
            self.check_timeline_consistency(),
            self.check_setting_completeness(),
        ]

    # ------------------------------------------------------------------
    # Check 1: 爽点密度 — at least 1 hook per 5 chapters
    # ------------------------------------------------------------------

    def check_hook_density(self) -> dict:
        """1. 爽点密度达标：每 5 章至少 1 个爽点."""
        hook_points = self.skeleton.get("hook_points", [])
        total = len(self.chapter_outlines)
        expected = max(1, total // 5)
        passed = len(hook_points) >= expected
        return {
            "name": "爽点密度",
            "passed": passed,
            "detail": f"需要 {expected} 个爽点，实际 {len(hook_points)} 个",
            "suggestion": "增加高潮/反转节点" if not passed else None,
        }

    # ------------------------------------------------------------------
    # Check 2: Strand 比例 — main strand >= 50% of chapters
    # ------------------------------------------------------------------

    def check_strand_ratio(self) -> dict:
        """2. Strand 比例合理：主线占比 >= 50%."""
        strands = self.skeleton.get("strands", [])
        if not strands:
            return {
                "name": "Strand比例",
                "passed": False,
                "detail": "无 Strand 数据",
                "suggestion": "添加 Strand 规划",
            }
        main_strand = next((s for s in strands if s["name"] == "主线"), None)
        if not main_strand:
            return {
                "name": "Strand比例",
                "passed": False,
                "detail": "缺少主线",
                "suggestion": "添加主线 Strand",
            }
        total_chapters = len(self.chapter_outlines)
        main_ratio = len(main_strand.get("chapters", [])) / max(total_chapters, 1)
        passed = main_ratio >= 0.5
        return {
            "name": "Strand比例",
            "passed": passed,
            "detail": f"主线占比 {main_ratio:.0%}",
            "suggestion": "主线章节占比应 >= 50%" if not passed else None,
        }

    # ------------------------------------------------------------------
    # Check 3: 总纲一致性 — used strands are all defined
    # ------------------------------------------------------------------

    def check_outline_consistency(self) -> dict:
        """3. 总纲一致性：章节大纲使用的 strand 必须在卷骨架中定义."""
        defined_strands = {s["name"] for s in self.skeleton.get("strands", [])}
        used_strands = {o.get("strand", "") for o in self.chapter_outlines}
        undefined = used_strands - defined_strands - {""}
        passed = len(undefined) == 0
        return {
            "name": "总纲一致性",
            "passed": passed,
            "detail": f"未定义的 Strand: {undefined}" if undefined else "一致",
            "suggestion": "在卷骨架中定义缺失的 Strand" if not passed else None,
        }

    # ------------------------------------------------------------------
    # Check 4: 约束频率 — each constraint triggered at least once
    # ------------------------------------------------------------------

    def check_constraint_frequency(self) -> dict:
        """4. 约束频率达标：每个约束至少触发一次."""
        triggers = self.skeleton.get("constraint_triggers", [])
        constraints = self.idea_bank.get("creativity_package", {}).get("constraints", [])
        if not constraints:
            return {
                "name": "约束频率",
                "passed": True,
                "detail": "无约束要求",
                "suggestion": None,
            }
        passed = len(triggers) >= len(constraints)
        return {
            "name": "约束频率",
            "passed": passed,
            "detail": f"约束 {len(constraints)} 条，触发点 {len(triggers)} 个",
            "suggestion": "为未触发的约束添加触发点" if not passed else None,
        }

    # ------------------------------------------------------------------
    # Check 5: 章节大纲完整性 — every chapter has required fields
    # ------------------------------------------------------------------

    def check_chapter_completeness(self) -> dict:
        """5. 章节大纲完整性：每章必须有 title/summary/conflict."""
        required_fields = ["title", "summary", "conflict"]
        incomplete = []
        for outline in self.chapter_outlines:
            missing = [f for f in required_fields if not outline.get(f)]
            if missing:
                incomplete.append({"chapter": outline["chapter"], "missing": missing})
        passed = len(incomplete) == 0
        return {
            "name": "章节完整性",
            "passed": passed,
            "detail": f"{len(incomplete)} 章不完整" if incomplete else "全部完整",
            "suggestion": f"补全以下章节：{incomplete[:3]}" if not passed else None,
        }

    # ------------------------------------------------------------------
    # Check 6: 时间线一致性 — day values never decrease
    # ------------------------------------------------------------------

    def check_timeline_consistency(self) -> dict:
        """6. 时间线无矛盾：day 单调递增（允许相等）."""
        timeline = self.timeline
        if not timeline:
            return {
                "name": "时间线一致性",
                "passed": True,
                "detail": "无时间线数据",
                "suggestion": None,
            }
        violations = []
        for i in range(1, len(timeline)):
            if timeline[i].get("day", 0) < timeline[i - 1].get("day", 0):
                violations.append(
                    f"事件{i}: day {timeline[i]['day']} < 前一事件 day {timeline[i-1]['day']}"
                )
        passed = len(violations) == 0
        return {
            "name": "时间线一致性",
            "passed": passed,
            "detail": f"{len(violations)} 处时间倒流" if violations else "无矛盾",
            "suggestion": violations[0] if violations else None,
        }

    # ------------------------------------------------------------------
    # Check 7: 设定补全 — settings dict is non-empty
    # ------------------------------------------------------------------

    def check_setting_completeness(self) -> dict:
        """7. 设定补全无遗漏：设定集非空."""
        settings = self.context.get("settings", {})
        passed = len(settings) > 0
        return {
            "name": "设定补全",
            "passed": passed,
            "detail": f"设定集 {len(settings)} 个文件" if settings else "设定集为空",
            "suggestion": "运行设定基线构建" if not passed else None,
        }
