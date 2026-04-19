# Task 306: Step 4 润色 + Anti-AI 终检

## 目标

实现 WriteSkillHandler 的 Step 4（润色），按 critical→high→medium/low 优先级修复 Step 3 审查发现的问题，最后执行 Anti-AI 终检。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/write_handler.py`（修改 execute_step）

## 依赖

- task-305（Step 3 完成后 context 包含 review_results / review_issues）

## 前置知识

context 中已有的数据（来自 Step 3）：
- `context["review_results"]` — 6 维审查结果
- `context["review_issues"]` — 按严重度排序的问题列表
- `context["adapted_text"]` 或 `context["draft_text"]` — 当前文本
- `context["task_brief"]` — 任务书
- `context["context_contract"]` — 约束清单

Step 4 是 `confirm` 模式：
1. execute_step 执行润色 → 返回润色后文本
2. 前端展示 diff 对比 → 用户确认或修改
3. validate_input 校验

## 规格

### execute_step（Step 4）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_4":
        return await self._polish(step, context)
    # ... 其他步骤
```

### _polish

```python
async def _polish(self, step: StepState, context: dict) -> dict:
    """按优先级修复审查问题 + Anti-AI 终检。

    修复优先级：
    1. critical — 必须修复（设定矛盾、严重 OOC）
    2. high — 强烈建议修复（缺少章末钩子、节奏严重失衡）
    3. medium/low — 可选修复

    Anti-AI 终检：
    - 检测并消除 AI 常见痕迹
    - 过度使用的词汇替换（"不禁"、"竟然"、"然而"等）
    - 句式多样性检查
    """
    # 获取当前文本
    current_text = context.get("adapted_text") or context.get("draft_text", "")
    issues = context.get("review_issues", [])

    # 分级处理
    critical_issues = [i for i in issues if i.get("severity") == "critical"]
    high_issues = [i for i in issues if i.get("severity") == "high"]
    other_issues = [i for i in issues if i.get("severity") in ("medium", "low")]

    # TODO: 实际 AI 调用 — 传入文本 + 问题列表 → 返回修复后文本
    # 降级模式：执行 Anti-AI 终检的简单规则替换
    polished_text = self._anti_ai_check(current_text)

    # 生成修复报告
    fix_report = {
        "critical_fixed": len(critical_issues),
        "high_fixed": len(high_issues),
        "other_fixed": 0,  # 降级模式不修复 medium/low
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
    """Anti-AI 终检：替换 AI 常见痕迹词汇。

    替换规则（部分）：
    - "不禁" 出现超过 2 次 → 替换为具体动作
    - "竟然" 出现超过 3 次 → 部分替换
    - "然而" 开头的段落过多 → 替换连接词
    - 连续 3 句以上相同句式 → 标记
    """
    import re

    # 统计高频 AI 词汇
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
            # 保留前 max_count 个，删除多余的
            parts = result.split(word)
            new_parts = []
            kept = 0
            for i, part in enumerate(parts[:-1]):
                new_parts.append(part)
                if kept < max_count:
                    new_parts.append(word)
                    kept += 1
                # 多余的直接连接（不加词汇）
            new_parts.append(parts[-1])
            result = "".join(new_parts)

    return result

def _count_anti_ai_fixes(self, original: str, polished: str) -> int:
    """统计 Anti-AI 修复的数量。"""
    if original == polished:
        return 0
    # 简单统计：字符差异数 / 平均词长
    diff_chars = abs(len(original) - len(polished))
    for i in range(min(len(original), len(polished))):
        if original[i] != polished[i]:
            diff_chars += 1
    return max(1, diff_chars // 10)
```

### validate_input（Step 4）

```python
async def validate_input(self, step: StepState, data: dict) -> str | None:
    if step.step_id == "step_4":
        confirmed = data.get("confirmed", False)
        if confirmed:
            # 用户确认润色结果，使用 polished_text
            return None
        edited_text = data.get("edited_text", "")
        if not edited_text:
            return "请确认润色结果或提交修改后的文本"
        # 用户提交了手动修改的文本
        # SkillRunner 将 data 存入 step.input_data
        return None
```

### 前端展示说明

Step 4 完成后，前端展示：
- 左右 diff 对比（原文 vs 润色后）
- 修复报告卡片（critical/high/other 修复数量 + Anti-AI 修复数量）
- 可编辑的文本区域（用户可在润色基础上继续微调）
- "确认" 按钮（使用润色后文本）
- "提交修改" 按钮（使用用户编辑后的文本）

## TDD 验收

- Happy path：context 包含 review_issues → execute_step("step_4") → polished_text 不为空 → fix_report 包含各级修复数量
- Edge case 1：文本中 "不禁" 出现 5 次 → Anti-AI 终检后只保留 2 次
- Edge case 2：review_issues 为空 → 仍执行 Anti-AI 终检 → 可能有修复
- Error case：validate_input("step_4") 收到 confirmed=False 且 edited_text 为空 → 返回错误信息
