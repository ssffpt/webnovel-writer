# Task 202: Step 4 节拍表 + Step 4.5 时间线

## 目标

实现 PlanSkillHandler 的 Step 4（生成卷节拍表）和 Step 4.5（生成卷时间线表），均为 auto→confirm 模式。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/plan_handler.py`（修改 execute_step + validate_input）

## 依赖

- task-201（PlanSkillHandler 骨架 + Step 1-3 已完成，context 中有 outline/settings/volume 信息）

## 前置知识

Step 4 和 Step 4.5 的交互模式是 `confirm`：
1. SkillRunner 进入该步骤 → 调用 `execute_step()` 生成 output_data
2. output_data 返回给前端展示（节拍表/时间线卡片）
3. 用户确认或提出修改意见 → 调用 `submit_input()` 提交
4. `validate_input()` 校验 → 通过后 advance

context 中已有的数据（来自 Step 1-3）：
- `context["outline"]` — 总纲 markdown 文本
- `context["settings"]` — 设定集 dict
- `context["idea_bank"]` — 创意约束包
- `context["volume_name"]` — 用户选择的卷名（Step 3 提交后由 SkillRunner 合并）
- `context["chapter_start"]` / `context["chapter_end"]` — 章节范围
- `context["volume_theme"]` — 本卷主题
- `context["special_requirements"]` — 特殊需求

## 规格

### execute_step（Step 4 — 节拍表）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_4":
        return await self._generate_beat_sheet(context)
    if step.step_id == "step_4_5":
        return await self._generate_timeline(context)
    # ... 其他步骤
```

### _generate_beat_sheet

```python
async def _generate_beat_sheet(self, context: dict) -> dict:
    """调用 AI API 生成卷节拍表。

    节拍表结构：按章节顺序排列的关键事件节点。
    每个节拍包含：章节位置、事件描述、情绪曲线、爽点标记。

    降级模式（无 AI API 时）：返回基于章节数的模板节拍表。
    """
    volume_name = context.get("volume_name", "")
    chapter_start = int(context.get("chapter_start", 1))
    chapter_end = int(context.get("chapter_end", 12))
    total_chapters = chapter_end - chapter_start + 1
    outline = context.get("outline", "")
    volume_theme = context.get("volume_theme", "")
    idea_bank = context.get("idea_bank", {})

    # TODO: 实际 AI 调用
    # 降级模式：生成模板节拍表
    beats = self._fallback_beat_sheet(total_chapters, chapter_start, volume_theme)

    context["beat_sheet"] = beats

    return {
        "beats": beats,
        "total_chapters": total_chapters,
        "instruction": "请确认以下节拍表，或提出修改意见",
    }

def _fallback_beat_sheet(self, total_chapters: int, chapter_start: int, theme: str) -> list[dict]:
    """无 AI 时的降级模板节拍表。"""
    beats = []
    # 三幕结构：25% 开端 / 50% 发展 / 25% 高潮
    act1_end = total_chapters // 4
    act2_end = act1_end + total_chapters // 2
    # act3 = 剩余

    for i in range(total_chapters):
        chapter_num = chapter_start + i
        if i < act1_end:
            act = "开端"
            emotion = "期待"
        elif i < act2_end:
            act = "发展"
            emotion = "紧张"
        else:
            act = "高潮"
            emotion = "爆发"

        beat = {
            "chapter": chapter_num,
            "act": act,
            "event": f"第{chapter_num}章事件（待 AI 生成）",
            "emotion_curve": emotion,
            "is_climax": i == total_chapters - 1 or i == act1_end - 1,
            "hook_type": "cliffhanger" if i % 3 == 2 else "curiosity",
        }
        beats.append(beat)

    return beats
```

### _generate_timeline

```python
async def _generate_timeline(self, context: dict) -> dict:
    """调用 AI API 生成卷时间线表。

    时间线结构：按时间顺序排列的事件，标注并行线索。
    每个事件包含：时间点、地点、涉及角色、事件描述、所属 Strand。

    降级模式：基于节拍表生成简化时间线。
    """
    beats = context.get("beat_sheet", [])
    chapter_start = int(context.get("chapter_start", 1))
    chapter_end = int(context.get("chapter_end", 12))

    # TODO: 实际 AI 调用
    # 降级模式
    timeline = self._fallback_timeline(beats)

    context["timeline"] = timeline

    return {
        "timeline": timeline,
        "instruction": "请确认以下时间线，或提出修改意见",
    }

def _fallback_timeline(self, beats: list[dict]) -> list[dict]:
    """无 AI 时的降级模板时间线。"""
    timeline = []
    for i, beat in enumerate(beats):
        event = {
            "day": i + 1,
            "chapter": beat["chapter"],
            "location": "待定",
            "characters": ["主角"],
            "event": beat["event"],
            "strand": "主线",
        }
        timeline.append(event)
    return timeline
```

### validate_input（Step 4 / Step 4.5 — 用户确认）

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_4":
        confirmed = data.get("confirmed", False)
        if not confirmed:
            # 用户提出修改意见
            feedback = data.get("feedback", "")
            if not feedback:
                return "请确认节拍表或提出修改意见"
            # 将反馈存入 context，可用于重新生成
            return None  # 接受反馈，advance（或可选：重新生成后再次 confirm）
        return None

    if step.step_id == "step_4_5":
        confirmed = data.get("confirmed", False)
        if not confirmed:
            feedback = data.get("feedback", "")
            if not feedback:
                return "请确认时间线或提出修改意见"
            return None
        return None

    # ... 其他步骤
```

### 节拍表数据结构（完整）

```python
# 单个节拍
{
    "chapter": 1,           # 章节编号
    "act": "开端",          # 所属幕：开端/发展/高潮/尾声
    "event": "主角初入宗门，遭遇排挤",  # 事件描述
    "emotion_curve": "期待",  # 情绪曲线标签
    "is_climax": False,     # 是否为高潮点
    "hook_type": "curiosity",  # 钩子类型：cliffhanger/curiosity/revelation/conflict
}

# 时间线事件
{
    "day": 1,               # 故事内时间（第N天）
    "chapter": 1,           # 对应章节
    "location": "青云宗外门",  # 地点
    "characters": ["主角", "师兄"],  # 涉及角色
    "event": "主角初入宗门",  # 事件描述
    "strand": "主线",       # 所属线索：主线/感情线/暗线/支线A...
}
```

## TDD 验收

- Happy path：context 包含完整 Step 1-3 数据 → execute_step("step_4") 返回 beats 列表 → 每个 beat 有 chapter/act/event/emotion_curve
- Edge case 1：execute_step("step_4_5") 基于 beat_sheet 生成 timeline → 每个事件有 day/chapter/strand
- Edge case 2：validate_input("step_4") 收到 confirmed=True → 返回 None
- Error case：validate_input("step_4") 收到 confirmed=False 且无 feedback → 返回错误信息
