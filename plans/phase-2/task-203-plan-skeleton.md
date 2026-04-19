# Task 203: Step 5 卷骨架

## 目标

实现 PlanSkillHandler 的 Step 5（生成卷骨架），auto→confirm 模式。卷骨架包含 Strand 规划、爽点密度、伏笔布局、约束触发点。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/plan_handler.py`（修改 execute_step + validate_input）

## 依赖

- task-202（Step 4/4.5 完成后 context 包含 beat_sheet 和 timeline）

## 前置知识

context 中已有的数据（来自 Step 1-4.5）：
- `context["outline"]` — 总纲 markdown
- `context["settings"]` — 设定集 dict
- `context["idea_bank"]` — 创意约束包（含 constraints 列表）
- `context["volume_name"]` — 卷名
- `context["chapter_start"]` / `context["chapter_end"]` — 章节范围
- `context["beat_sheet"]` — 节拍表（Step 4 产出）
- `context["timeline"]` — 时间线（Step 4.5 产出）

## 规格

### execute_step（Step 5）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_5":
        return await self._generate_volume_skeleton(context)
    # ... 其他步骤
```

### _generate_volume_skeleton

```python
async def _generate_volume_skeleton(self, context: dict) -> dict:
    """调用 AI API 生成卷骨架。

    卷骨架 = Strand 规划 + 爽点密度分布 + 伏笔布局 + 约束触发点。
    基于节拍表和时间线，生成更细粒度的结构规划。

    降级模式（无 AI API 时）：基于节拍表生成简化骨架。
    """
    beats = context.get("beat_sheet", [])
    timeline = context.get("timeline", [])
    idea_bank = context.get("idea_bank", {})
    chapter_start = int(context.get("chapter_start", 1))
    chapter_end = int(context.get("chapter_end", 12))
    total_chapters = chapter_end - chapter_start + 1

    # TODO: 实际 AI 调用
    # 降级模式
    skeleton = self._fallback_skeleton(beats, timeline, idea_bank, chapter_start, total_chapters)

    context["volume_skeleton"] = skeleton

    return {
        "skeleton": skeleton,
        "instruction": "请确认以下卷骨架，或提出修改意见",
    }

def _fallback_skeleton(
    self,
    beats: list[dict],
    timeline: list[dict],
    idea_bank: dict,
    chapter_start: int,
    total_chapters: int,
) -> dict:
    """无 AI 时的降级模板卷骨架。"""
    # 1. Strand 规划
    strands = [
        {"name": "主线", "description": "核心剧情推进", "chapters": list(range(chapter_start, chapter_start + total_chapters))},
        {"name": "感情线", "description": "感情关系发展", "chapters": list(range(chapter_start, chapter_start + total_chapters, 3))},
    ]

    # 2. 爽点密度分布（每 3-5 章一个爽点）
    hook_points = []
    for i in range(0, total_chapters, 4):
        ch = chapter_start + i
        hook_points.append({
            "chapter": ch,
            "type": "小高潮" if i % 8 != 0 else "大高潮",
            "description": f"第{ch}章爽点（待 AI 生成）",
        })

    # 3. 伏笔布局
    foreshadowing = [
        {
            "id": "foreshadow_1",
            "plant_chapter": chapter_start,
            "reveal_chapter": chapter_start + total_chapters - 1,
            "description": "伏笔（待 AI 生成）",
            "urgency": "low",
        },
    ]

    # 4. 约束触发点（从 idea_bank 的 constraints 映射）
    constraints = idea_bank.get("creativity_package", {}).get("constraints", [])
    constraint_triggers = []
    for i, c in enumerate(constraints):
        trigger_ch = chapter_start + (i * total_chapters // max(len(constraints), 1))
        constraint_triggers.append({
            "constraint": c.get("content", ""),
            "trigger_chapter": trigger_ch,
            "how": f"在第{trigger_ch}章触发此约束（待 AI 生成）",
        })

    return {
        "strands": strands,
        "hook_points": hook_points,
        "foreshadowing": foreshadowing,
        "constraint_triggers": constraint_triggers,
    }
```

### validate_input（Step 5 — 用户确认）

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_5":
        confirmed = data.get("confirmed", False)
        if not confirmed:
            feedback = data.get("feedback", "")
            if not feedback:
                return "请确认卷骨架或提出修改意见"
            return None
        return None
    # ... 其他步骤
```

### 卷骨架数据结构（完整）

```python
{
    "strands": [
        {
            "name": "主线",
            "description": "核心剧情推进",
            "chapters": [1, 2, 3, ...],  # 涉及章节
        },
    ],
    "hook_points": [
        {
            "chapter": 4,
            "type": "小高潮",       # 小高潮 / 大高潮 / 反转
            "description": "主角首次展示金手指",
        },
    ],
    "foreshadowing": [
        {
            "id": "foreshadow_1",
            "plant_chapter": 1,     # 埋设章节
            "reveal_chapter": 10,   # 揭示章节
            "description": "神秘老者的身份",
            "urgency": "low",       # low / medium / high
        },
    ],
    "constraint_triggers": [
        {
            "constraint": "每 5 章至少一个小高潮",
            "trigger_chapter": 5,
            "how": "通过比武大会实现",
        },
    ],
}
```

## TDD 验收

- Happy path：context 包含 beat_sheet + timeline → execute_step("step_5") 返回 skeleton → skeleton 包含 strands/hook_points/foreshadowing/constraint_triggers
- Edge case 1：idea_bank 无 constraints → constraint_triggers 为空列表，不报错
- Edge case 2：validate_input("step_5") 收到 confirmed=True → 返回 None
- Error case：validate_input("step_5") 收到 confirmed=False 且无 feedback → 返回错误信息
