# Task 304: Step 2A 正文起草 + Step 2B 风格适配

## 目标

实现 WriteSkillHandler 的 Step 2A（正文起草，auto→confirm）和 Step 2B（风格适配，auto→confirm）。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/write_handler.py`（修改 execute_step）

## 依赖

- task-303（Step 1 完成后 context 包含 task_brief / context_contract / execution_pack）

## 前置知识

context 中已有的数据（来自 Step 1）：
- `context["task_brief"]` — 7 板块任务书
- `context["context_contract"]` — 写作约束清单
- `context["execution_pack"]` — 写作执行包（含 word_target: {min: 2000, max: 2500}）
- `context["chapter_num"]` — 章节编号
- `context["mode"]` — standard / fast / minimal

Step 2A 和 2B 都是 `confirm` 模式：
1. execute_step 生成内容（草稿/风格适配后文本）
2. 返回给前端展示，用户可预览/微调
3. 用户确认或提交修改 → validate_input 校验

## 规格

### execute_step（Step 2A — 正文起草）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_2a":
        return await self._draft_chapter(context)
    if step.step_id == "step_2b":
        return await self._style_adapt(context)
    # ... 其他步骤
```

### _draft_chapter

```python
async def _draft_chapter(self, context: dict) -> dict:
    """调用 AI API 生成章节草稿。

    输入：execution_pack（含大纲、设定、约束等）
    输出：2000-2500 字正文草稿

    Prompt 要点：
    - 严格遵循本章大纲的事件安排
    - 遵守 Context Contract 中的设定约束
    - 字数控制在 2000-2500 字
    - 开头必须有钩子（承接上章或制造悬念）
    - 结尾必须有钩子（cliffhanger 或 curiosity）
    - 不得引入大纲中未提及的新设定

    降级模式（无 AI API 时）：返回模板占位文本。
    """
    execution_pack = context.get("execution_pack", {})
    task_brief = context.get("task_brief", {})
    chapter_num = context.get("chapter_num", 1)

    # TODO: 实际 AI 调用
    # 降级模式
    draft = self._fallback_draft(chapter_num, task_brief)

    context["draft_text"] = draft
    context["draft_word_count"] = len(draft)

    return {
        "draft_text": draft,
        "word_count": len(draft),
        "instruction": "请预览草稿，确认或修改后继续",
    }

def _fallback_draft(self, chapter_num: int, task_brief: dict) -> str:
    """无 AI 时的降级模板草稿。"""
    outline = task_brief.get("chapter_outline", "")
    return (
        f"# 第{chapter_num}章\n\n"
        f"[AI 草稿占位 — 基于大纲生成]\n\n"
        f"大纲摘要：{outline[:200] if outline else '无大纲'}\n\n"
        f"{'占位正文。' * 100}\n"
    )
```

### _style_adapt

```python
async def _style_adapt(self, context: dict) -> dict:
    """调用 AI API 进行风格适配。

    目标：消除三种 AI 腔调：
    1. 模板腔 — 固定句式、过度使用"然而"/"不禁"
    2. 说明腔 — 像百科全书一样解释设定
    3. 机械腔 — 缺乏情感、节奏单调

    输入：draft_text（Step 2A 的草稿）
    输出：风格适配后的文本 + diff 标记

    降级模式：返回原文不变。
    """
    draft_text = context.get("draft_text", "")
    style_reference = context.get("task_brief", {}).get("style_reference", "")

    # TODO: 实际 AI 调用
    # 降级模式：原文不变
    adapted_text = draft_text  # 降级时不做修改

    context["adapted_text"] = adapted_text

    # 生成 diff（简化：标记是否有变化）
    has_changes = adapted_text != draft_text

    return {
        "adapted_text": adapted_text,
        "has_changes": has_changes,
        "changes_summary": "风格适配完成" if has_changes else "无需调整（降级模式）",
        "instruction": "请确认风格适配结果",
    }
```

### validate_input 扩展

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_2a":
        confirmed = data.get("confirmed", False)
        if confirmed:
            # 用户确认原始草稿
            return None
        edited_text = data.get("edited_text", "")
        if not edited_text:
            return "请确认草稿或提交修改后的文本"
        # 用户提交了修改后的文本，更新 context
        # SkillRunner 会将 data 存入 step.input_data，后续步骤可从中读取
        return None

    if step.step_id == "step_2b":
        confirmed = data.get("confirmed", False)
        if confirmed:
            return None
        feedback = data.get("feedback", "")
        if not feedback:
            return "请确认风格适配结果或提出修改意见"
        return None

    # ... 其他步骤
```

### 前端展示说明

Step 2A 完成后，前端展示：
- 草稿全文（可编辑 textarea）
- 字数统计
- "确认" 按钮（使用原文）
- "提交修改" 按钮（使用用户编辑后的文本）

Step 2B 完成后，前端展示：
- 适配后全文
- 与原文的 diff 对比（高亮变化部分）
- "确认" 按钮
- "修改意见" 输入框 + 提交按钮

## TDD 验收

- Happy path：execute_step("step_2a") → 返回 draft_text（字数 > 0）→ context["draft_text"] 已设置
- Edge case 1：execute_step("step_2b") 降级模式 → adapted_text == draft_text → has_changes=False
- Edge case 2：validate_input("step_2a") 收到 confirmed=True → 返回 None
- Error case：validate_input("step_2a") 收到 confirmed=False 且 edited_text 为空 → 返回错误信息
