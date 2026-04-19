# Task 205: Step 7 回写设定集 + Step 8 验证

## 目标

实现 PlanSkillHandler 的 Step 7（回写设定集，新增事实写回，冲突标记 BLOCKER）和 Step 8（7 项验证检查）。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/plan_handler.py`（修改 execute_step）
- `webnovel-writer/dashboard/skill_handlers/plan_validator.py`（新建，验证逻辑）

## 依赖

- task-204（Step 6 完成后 context 包含 chapter_outlines）

## 前置知识

context 中已有的数据（来自 Step 1-6）：
- `context["project_root"]` — 项目根目录
- `context["settings"]` — 设定集 dict（文件名→内容）
- `context["volume_skeleton"]` — 卷骨架
- `context["chapter_outlines"]` — 章节大纲列表
- `context["beat_sheet"]` — 节拍表
- `context["timeline"]` — 时间线
- `context["outline"]` — 总纲
- `context["idea_bank"]` — 创意约束包

Step 7 是 `auto` 模式，但如果检测到冲突（BLOCKER），需要升级为 confirm 让用户决策。
实现方式：Step 7 execute_step 返回 output_data 中标记 `has_blockers: True`，SkillRunner 检测到后将步骤状态改为 `waiting_input`。

## 规格

### execute_step（Step 7 — 回写设定集）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_7":
        return await self._writeback_settings(step, context)
    if step.step_id == "step_8":
        return await self._validate_and_save(step, context)
    # ... 其他步骤
```

### _writeback_settings

```python
async def _writeback_settings(self, step: StepState, context: dict) -> dict:
    """将章节大纲中新增的设定事实回写到设定集文件。

    流程：
    1. 从 chapter_outlines 中提取新增事实（角色、地点、力量等）
    2. 与现有设定集对比，检测冲突
    3. 无冲突 → 直接追加写入
    4. 有冲突 → 标记 BLOCKER，等待用户决策
    """
    project_root = Path(context.get("project_root", "."))
    setting_dir = project_root / "设定集"
    chapter_outlines = context.get("chapter_outlines", [])
    existing_settings = context.get("settings", {})

    # 提取新增事实
    new_facts = self._extract_new_facts(chapter_outlines)

    # 检测冲突
    blockers = []
    additions = []

    for fact in new_facts:
        target_file = fact["target_file"]  # 如 "主要角色"
        content = existing_settings.get(target_file, "")

        if fact.get("conflicts_with"):
            # 与现有设定冲突
            blockers.append({
                "fact": fact["content"],
                "target_file": target_file,
                "conflict": fact["conflicts_with"],
                "suggestion": fact.get("resolution", "请手动决策"),
            })
        else:
            additions.append(fact)

    # 无冲突的直接写入
    for fact in additions:
        target_path = setting_dir / f"{fact['target_file']}.md"
        if target_path.exists():
            current = target_path.read_text(encoding="utf-8")
            target_path.write_text(
                current + f"\n\n### {fact['label']}\n\n{fact['content']}\n",
                encoding="utf-8",
            )

    context["writeback_additions"] = additions
    context["writeback_blockers"] = blockers

    result = {
        "additions_count": len(additions),
        "blockers": blockers,
        "has_blockers": len(blockers) > 0,
        "instruction": "设定集回写完成" if not blockers else "检测到设定冲突，请决策",
    }

    # 如果有 BLOCKER，SkillRunner 应将此步骤升级为 waiting_input
    # 通过 output_data 中的 has_blockers 标记通知 SkillRunner
    if blockers:
        result["requires_input"] = True  # SkillRunner 检测此字段决定是否等待用户输入

    return result

def _extract_new_facts(self, chapter_outlines: list[dict]) -> list[dict]:
    """从章节大纲中提取新增设定事实。

    降级模式：返回空列表（无 AI 时不做自动提取）。
    """
    # TODO: 实际 AI 调用，分析 chapter_outlines 中的新角色/地点/力量等
    # 降级模式
    return []
```

### validate_input（Step 7 — BLOCKER 决策）

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_7":
        # 用户对每个 BLOCKER 做出决策
        decisions = data.get("blocker_decisions", [])
        # decisions = [{"blocker_index": 0, "action": "accept" | "reject" | "modify", "modified_content": "..."}]
        if not decisions:
            return "请对每个冲突做出决策"
        return None
    # ... 其他步骤
```

### _validate_and_save（Step 8 — 7 项验证）

```python
async def _validate_and_save(self, step: StepState, context: dict) -> dict:
    """执行 7 项验证检查，全部通过后保存文件。"""
    from .plan_validator import PlanValidator

    validator = PlanValidator(context)
    results = validator.run_all_checks()

    all_passed = all(r["passed"] for r in results)

    if all_passed:
        # 保存文件
        await self._save_plan_files(context)

    context["validation_results"] = results
    context["plan_saved"] = all_passed

    return {
        "validation_results": results,
        "all_passed": all_passed,
        "instruction": "验证全部通过，文件已保存" if all_passed else "以下验证项未通过",
    }

async def _save_plan_files(self, context: dict) -> None:
    """将生成的大纲文件写入磁盘。"""
    project_root = Path(context.get("project_root", "."))
    volume_name = context.get("volume_name", "第一卷")
    chapter_outlines = context.get("chapter_outlines", [])
    beat_sheet = context.get("beat_sheet", [])
    timeline = context.get("timeline", [])
    skeleton = context.get("volume_skeleton", {})

    # 创建卷目录
    volume_dir = project_root / "大纲" / volume_name
    volume_dir.mkdir(parents=True, exist_ok=True)

    # 1. 写入节拍表
    beat_path = volume_dir / "节拍表.json"
    beat_path.write_text(json.dumps(beat_sheet, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. 写入时间线
    timeline_path = volume_dir / "时间线.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3. 写入卷骨架
    skeleton_path = volume_dir / "卷骨架.json"
    skeleton_path.write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding="utf-8")

    # 4. 写入章节大纲
    for outline in chapter_outlines:
        ch_num = outline["chapter"]
        ch_path = volume_dir / f"第{ch_num}章.json"
        ch_path.write_text(json.dumps(outline, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. 更新 state.json
    state_path = project_root / ".webnovel" / "state.json"
    state = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    if "volumes" not in state:
        state["volumes"] = {}
    state["volumes"][volume_name] = {
        "status": "planned",
        "chapter_start": context.get("chapter_start"),
        "chapter_end": context.get("chapter_end"),
        "chapters_count": len(chapter_outlines),
    }
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
```

### plan_validator.py

```python
"""PlanValidator — 7 项验证检查。"""

import json


class PlanValidator:
    def __init__(self, context: dict):
        self.context = context
        self.chapter_outlines = context.get("chapter_outlines", [])
        self.beat_sheet = context.get("beat_sheet", [])
        self.timeline = context.get("timeline", [])
        self.skeleton = context.get("volume_skeleton", {})
        self.outline = context.get("outline", "")
        self.idea_bank = context.get("idea_bank", {})

    def run_all_checks(self) -> list[dict]:
        """执行全部 7 项验证，返回结果列表。"""
        return [
            self.check_hook_density(),
            self.check_strand_ratio(),
            self.check_outline_consistency(),
            self.check_constraint_frequency(),
            self.check_chapter_completeness(),
            self.check_timeline_consistency(),
            self.check_setting_completeness(),
        ]

    def check_hook_density(self) -> dict:
        """1. 爽点密度达标：每 5 章至少 1 个爽点。"""
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

    def check_strand_ratio(self) -> dict:
        """2. Strand 比例合理：主线占比 >= 50%。"""
        strands = self.skeleton.get("strands", [])
        if not strands:
            return {"name": "Strand比例", "passed": False, "detail": "无 Strand 数据", "suggestion": "添加 Strand 规划"}
        main_strand = next((s for s in strands if s["name"] == "主线"), None)
        if not main_strand:
            return {"name": "Strand比例", "passed": False, "detail": "缺少主线", "suggestion": "添加主线 Strand"}
        total_chapters = len(self.chapter_outlines)
        main_ratio = len(main_strand.get("chapters", [])) / max(total_chapters, 1)
        passed = main_ratio >= 0.5
        return {
            "name": "Strand比例",
            "passed": passed,
            "detail": f"主线占比 {main_ratio:.0%}",
            "suggestion": "主线章节占比应 >= 50%" if not passed else None,
        }

    def check_outline_consistency(self) -> dict:
        """3. 总纲一致性：章节大纲不与总纲矛盾。"""
        # 简化检查：确认所有章节大纲的 strand 在 skeleton 中有定义
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

    def check_constraint_frequency(self) -> dict:
        """4. 约束频率达标：每个约束至少触发一次。"""
        triggers = self.skeleton.get("constraint_triggers", [])
        constraints = self.idea_bank.get("creativity_package", {}).get("constraints", [])
        if not constraints:
            return {"name": "约束频率", "passed": True, "detail": "无约束要求", "suggestion": None}
        passed = len(triggers) >= len(constraints)
        return {
            "name": "约束频率",
            "passed": passed,
            "detail": f"约束 {len(constraints)} 条，触发点 {len(triggers)} 个",
            "suggestion": "为未触发的约束添加触发点" if not passed else None,
        }

    def check_chapter_completeness(self) -> dict:
        """5. 章节大纲完整性：每章必须有 title/summary/conflict。"""
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

    def check_timeline_consistency(self) -> dict:
        """6. 时间线无矛盾：时间不倒流（day 单调递增或相等）。"""
        timeline = self.timeline
        if not timeline:
            return {"name": "时间线一致性", "passed": True, "detail": "无时间线数据", "suggestion": None}
        violations = []
        for i in range(1, len(timeline)):
            if timeline[i].get("day", 0) < timeline[i - 1].get("day", 0):
                violations.append(f"事件{i}: day {timeline[i]['day']} < 前一事件 day {timeline[i-1]['day']}")
        passed = len(violations) == 0
        return {
            "name": "时间线一致性",
            "passed": passed,
            "detail": f"{len(violations)} 处时间倒流" if violations else "无矛盾",
            "suggestion": violations[0] if violations else None,
        }

    def check_setting_completeness(self) -> dict:
        """7. 设定补全无遗漏：章节大纲中出现的角色/地点在设定集中有记录。"""
        # 简化检查：确认设定集非空
        settings = self.context.get("settings", {})
        passed = len(settings) > 0
        return {
            "name": "设定补全",
            "passed": passed,
            "detail": f"设定集 {len(settings)} 个文件" if settings else "设定集为空",
            "suggestion": "运行设定基线构建" if not passed else None,
        }
```

## TDD 验收

- Happy path：context 完整 → Step 7 无冲突 → 直接写入 → Step 8 全部通过 → 文件保存成功
- Edge case 1：Step 7 检测到 BLOCKER → output_data.has_blockers=True → requires_input=True
- Edge case 2：Step 8 爽点密度不达标 → validation_results 中该项 passed=False，all_passed=False
- Error case：chapter_outlines 为空 → Step 8 章节完整性检查 passed=True（无章节=无不完整）
