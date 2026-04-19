# Task 204: Step 6 章节大纲批量生成

## 目标

实现 PlanSkillHandler 的 Step 6（生成章节大纲），auto 模式，分批生成，每批 4-5 章，通过 SSE 推送批次进度。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/plan_handler.py`（修改 execute_step）

## 依赖

- task-203（Step 5 完成后 context 包含 volume_skeleton）

## 前置知识

context 中已有的数据（来自 Step 1-5）：
- `context["outline"]` — 总纲
- `context["settings"]` — 设定集
- `context["beat_sheet"]` — 节拍表
- `context["timeline"]` — 时间线
- `context["volume_skeleton"]` — 卷骨架（含 strands/hook_points/foreshadowing/constraint_triggers）
- `context["volume_name"]` — 卷名
- `context["chapter_start"]` / `context["chapter_end"]` — 章节范围

SkillRunner 的 `on_step_change` 回调可用于推送进度。StepState 有 `progress: float` 字段（0.0~1.0），execute_step 中可通过修改 step.progress 触发 SSE 推送。

## 规格

### execute_step（Step 6）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_6":
        return await self._generate_chapter_outlines(step, context)
    # ... 其他步骤
```

### _generate_chapter_outlines

```python
async def _generate_chapter_outlines(self, step: StepState, context: dict) -> dict:
    """分批生成章节大纲。

    每章大纲包含 16 个字段（见下方数据结构）。
    分批生成（每批 4-5 章），通过 step.progress 推送进度。

    降级模式（无 AI API 时）：生成模板大纲。
    """
    chapter_start = int(context.get("chapter_start", 1))
    chapter_end = int(context.get("chapter_end", 12))
    beats = context.get("beat_sheet", [])
    skeleton = context.get("volume_skeleton", {})
    total_chapters = chapter_end - chapter_start + 1

    BATCH_SIZE = 4
    chapter_outlines = []

    for batch_start in range(0, total_chapters, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_chapters)
        batch_chapters = list(range(
            chapter_start + batch_start,
            chapter_start + batch_end,
        ))

        # 更新进度
        step.progress = batch_start / total_chapters
        # SkillRunner 会在 progress 变化时触发 on_step_change → SSE 推送

        # 获取本批次对应的节拍
        batch_beats = [b for b in beats if b["chapter"] in batch_chapters]

        # TODO: 实际 AI 调用，传入 outline + settings + beats + skeleton
        # 降级模式
        batch_outlines = self._fallback_chapter_outlines(batch_chapters, batch_beats, skeleton)
        chapter_outlines.extend(batch_outlines)

    step.progress = 1.0
    context["chapter_outlines"] = chapter_outlines

    return {
        "chapter_outlines": chapter_outlines,
        "total_generated": len(chapter_outlines),
        "instruction": f"已生成 {len(chapter_outlines)} 章大纲",
    }

def _fallback_chapter_outlines(
    self,
    chapters: list[int],
    beats: list[dict],
    skeleton: dict,
) -> list[dict]:
    """无 AI 时的降级模板章节大纲。"""
    outlines = []
    hook_chapters = {hp["chapter"] for hp in skeleton.get("hook_points", [])}

    for i, ch_num in enumerate(chapters):
        beat = beats[i] if i < len(beats) else {}
        outline = {
            "chapter": ch_num,
            "title": f"第{ch_num}章",
            "pov": "主角",
            "location": "待定",
            "time": f"第{ch_num}天",
            "summary": beat.get("event", f"第{ch_num}章剧情（待 AI 生成）"),
            "opening_hook": "悬念开场（待生成）",
            "closing_hook": "章末钩子（待生成）",
            "key_events": [beat.get("event", "主要事件")] if beat else ["主要事件"],
            "character_goals": ["主角目标（待生成）"],
            "conflict": "本章冲突（待生成）",
            "emotion_arc": beat.get("emotion_curve", "平稳"),
            "strand": "主线",
            "foreshadowing_plant": [],
            "foreshadowing_reveal": [],
            "is_climax": ch_num in hook_chapters,
            "word_target": 2200,
        }
        outlines.append(outline)

    return outlines
```

### 章节大纲数据结构（16 字段）

```python
{
    "chapter": 1,                    # 章节编号
    "title": "初入宗门",             # 章节标题
    "pov": "主角",                   # 视角角色
    "location": "青云宗外门",        # 主要场景
    "time": "第1天·清晨",           # 故事内时间
    "summary": "主角初入宗门...",    # 200字以内剧情摘要
    "opening_hook": "以主角被拒门外开场", # 开场钩子
    "closing_hook": "发现神秘令牌",  # 章末钩子
    "key_events": [                  # 关键事件列表（2-4个）
        "入门测试",
        "遭遇排挤",
    ],
    "character_goals": [             # 本章角色目标
        "通过入门测试",
    ],
    "conflict": "外门弟子排挤新人",  # 本章核心冲突
    "emotion_arc": "期待→受挫→坚定", # 情绪弧线
    "strand": "主线",               # 所属 Strand
    "foreshadowing_plant": [         # 本章埋设的伏笔 ID
        "foreshadow_1",
    ],
    "foreshadowing_reveal": [],      # 本章揭示的伏笔 ID
    "is_climax": False,             # 是否为高潮章节
    "word_target": 2200,            # 目标字数
}
```

### 进度推送说明

SkillRunner 在 execute_step 执行期间，检测到 step.progress 变化时，通过 on_step_change 回调触发 SSE 事件：

```json
{
  "type": "skill.step",
  "skillId": "xxx",
  "step": {
    "id": "step_6",
    "name": "生成章节大纲",
    "status": "running",
    "progress": 0.33
  },
  "log": "正在生成第 5/12 章..."
}
```

前端根据 progress 值显示进度条和当前批次信息。

## TDD 验收

- Happy path：context 包含完整 Step 1-5 数据 → execute_step("step_6") 返回 chapter_outlines → 数量等于 chapter_end - chapter_start + 1 → 每个大纲有 16 个字段
- Edge case 1：单章卷（chapter_start == chapter_end - 1）→ 只生成 1 章大纲，不分批
- Edge case 2：step.progress 在生成过程中从 0.0 递增到 1.0
- Error case：beat_sheet 为空 → 仍能生成模板大纲，不报错
