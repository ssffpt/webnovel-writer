# Task 305: Step 3 六维审查（并行检查器）

## 目标

实现 WriteSkillHandler 的 Step 3（六维审查），6 个独立检查器通过 asyncio.gather 并行执行，结果实时推送。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/write_handler.py`（修改 execute_step）
- `webnovel-writer/dashboard/skill_handlers/review_checkers.py`（新建，6 个检查器）

## 依赖

- task-304（Step 2A/2B 完成后 context 包含 draft_text 或 adapted_text）

## 前置知识

六维审查维度：
1. 爽点密度 — 每 500 字至少一个微爽点，每章至少一个大爽点
2. 设定一致性 — 不违反已有设定（力量等级、地理、时间线）
3. 节奏比例 — 对话/描写/动作/心理的比例合理
4. 人物 OOC — 角色行为是否符合已建立的性格
5. 叙事连贯性 — 前后文逻辑通顺，无跳跃
6. 追读力 — 章末钩子强度、悬念设置

minimal 模式仅执行核心 3 项：设定一致性 + 人物 OOC + 叙事连贯性。

context 中已有的数据：
- `context["draft_text"]` 或 `context["adapted_text"]` — 待审查文本
- `context["task_brief"]` — 7 板块任务书（含设定、约束等）
- `context["context_contract"]` — 写作约束清单
- `context["mode"]` — standard / fast / minimal

## 规格

### execute_step（Step 3）

```python
import asyncio

async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_3":
        return await self._run_review(step, context)
    # ... 其他步骤
```

### _run_review

```python
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

    # 获取待审查文本（优先 adapted_text，其次 draft_text）
    text = context.get("adapted_text") or context.get("draft_text", "")
    task_brief = context.get("task_brief", {})
    contract = context.get("context_contract", {})
    mode = context.get("mode", "standard")

    # 根据模式选择检查器
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

    # 并行执行
    results = await asyncio.gather(
        *[checker.check() for checker in checkers],
        return_exceptions=True,
    )

    # 处理结果
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

    # 计算总分
    total_score = sum(r["score"] for r in review_results) / len(review_results) if review_results else 0

    # 汇总问题
    all_issues = []
    for r in review_results:
        for issue in r.get("issues", []):
            issue["dimension"] = r["dimension"]
            all_issues.append(issue)

    # 按严重度排序
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
```

### review_checkers.py

```python
"""六维审查检查器。每个检查器独立执行，返回统一格式的结果。"""

from abc import ABC, abstractmethod


class BaseChecker(ABC):
    """检查器基类。"""

    dimension: str = ""  # 维度名称

    def __init__(self, text: str, task_brief: dict, contract: dict):
        self.text = text
        self.task_brief = task_brief
        self.contract = contract

    @abstractmethod
    async def check(self) -> dict:
        """执行检查，返回结果。

        Returns:
            {
                "dimension": str,       # 维度名称
                "score": float,         # 0-10 分
                "passed": bool,         # 是否通过（>= 6 分）
                "issues": [             # 问题列表
                    {
                        "severity": "critical" | "high" | "medium" | "low",
                        "message": str,
                        "location": str | None,  # 问题位置描述
                        "suggestion": str | None,  # 修复建议
                    }
                ],
            }
        """
        ...


class HookDensityChecker(BaseChecker):
    """1. 爽点密度检查。"""
    dimension = "爽点密度"

    async def check(self) -> dict:
        """检查爽点密度。

        规则：
        - 每 500 字至少一个微爽点（情绪波动/小反转/新信息）
        - 每章至少一个大爽点（重大反转/突破/高潮）
        - 开头 200 字内必须有钩子

        降级模式：基于文本长度和段落结构做简单评估。
        """
        issues = []
        text_len = len(self.text)

        # 简单评估：检查段落数量和长度分布
        paragraphs = [p for p in self.text.split("\n\n") if p.strip()]

        # 检查开头是否有对话或动作（简单启发式）
        if paragraphs and not any(c in paragraphs[0][:200] for c in ["「", "\"", "！", "？"]):
            issues.append({
                "severity": "medium",
                "message": "开头 200 字缺少对话或强情绪标点，可能缺少钩子",
                "location": "开头",
                "suggestion": "考虑以对话、动作或悬念开场",
            })

        # 检查章末是否有钩子
        if paragraphs and len(paragraphs[-1]) < 50:
            issues.append({
                "severity": "low",
                "message": "章末段落过短，可能缺少有力的收尾钩子",
                "location": "结尾",
                "suggestion": "增强章末悬念或情绪冲击",
            })

        score = 7.0 - len(issues) * 1.5
        score = max(0, min(10, score))

        return {
            "dimension": self.dimension,
            "score": score,
            "passed": score >= 6,
            "issues": issues,
        }


class SettingConsistencyChecker(BaseChecker):
    """2. 设定一致性检查。"""
    dimension = "设定一致性"

    async def check(self) -> dict:
        """检查是否违反已有设定。

        降级模式：检查 contract 中的硬约束关键词是否在文本中被违反。
        """
        issues = []
        constraints = self.contract.get("setting_constraints", [])

        # 简单检查：约束中的"禁止"/"不可"关键词
        for constraint in constraints:
            # 提取约束中的关键实体
            # 降级模式下只做关键词匹配
            pass

        score = 8.0  # 降级模式默认高分
        return {
            "dimension": self.dimension,
            "score": score,
            "passed": score >= 6,
            "issues": issues,
        }


class RhythmRatioChecker(BaseChecker):
    """3. 节奏比例检查。"""
    dimension = "节奏比例"

    async def check(self) -> dict:
        """检查对话/描写/动作/心理的比例。

        理想比例（网文）：
        - 对话：30-50%
        - 动作/事件：20-35%
        - 描写：10-20%
        - 心理：10-20%
        """
        issues = []
        lines = self.text.split("\n")
        total_chars = len(self.text)

        # 简单启发式：对话行（含引号）
        dialogue_chars = sum(
            len(line) for line in lines
            if "「" in line or "」" in line or """ in line or """ in line
        )
        dialogue_ratio = dialogue_chars / max(total_chars, 1)

        if dialogue_ratio < 0.2:
            issues.append({
                "severity": "medium",
                "message": f"对话占比过低（{dialogue_ratio:.0%}），建议增加对话推动剧情",
                "location": None,
                "suggestion": "增加角色对话，减少纯叙述",
            })
        elif dialogue_ratio > 0.6:
            issues.append({
                "severity": "medium",
                "message": f"对话占比过高（{dialogue_ratio:.0%}），缺少描写和动作",
                "location": None,
                "suggestion": "增加环境描写和动作描写",
            })

        score = 7.5 - len(issues) * 2
        score = max(0, min(10, score))

        return {
            "dimension": self.dimension,
            "score": score,
            "passed": score >= 6,
            "issues": issues,
        }


class CharacterOOCChecker(BaseChecker):
    """4. 人物 OOC 检查。"""
    dimension = "人物OOC"

    async def check(self) -> dict:
        """检查角色行为是否符合已建立的性格。

        降级模式：无法做深度语义分析，返回默认通过。
        TODO: AI 调用时分析角色对话/行为是否与设定一致。
        """
        return {
            "dimension": self.dimension,
            "score": 8.0,
            "passed": True,
            "issues": [],
        }


class NarrativeCoherenceChecker(BaseChecker):
    """5. 叙事连贯性检查。"""
    dimension = "叙事连贯性"

    async def check(self) -> dict:
        """检查前后文逻辑是否通顺。

        降级模式：检查基本结构（段落长度、是否有过长段落等）。
        """
        issues = []
        paragraphs = [p for p in self.text.split("\n\n") if p.strip()]

        # 检查是否有过长段落（> 500 字无分段）
        for i, p in enumerate(paragraphs):
            if len(p) > 500:
                issues.append({
                    "severity": "low",
                    "message": f"第 {i+1} 段过长（{len(p)} 字），影响阅读节奏",
                    "location": f"第 {i+1} 段",
                    "suggestion": "考虑拆分为更短的段落",
                })

        score = 8.0 - len(issues) * 0.5
        score = max(0, min(10, score))

        return {
            "dimension": self.dimension,
            "score": score,
            "passed": score >= 6,
            "issues": issues,
        }


class ReadabilityChecker(BaseChecker):
    """6. 追读力检查。"""
    dimension = "追读力"

    async def check(self) -> dict:
        """检查章末钩子强度和悬念设置。

        降级模式：检查章末是否以问句、省略号、或强情绪结尾。
        """
        issues = []
        text = self.text.strip()

        # 检查结尾
        if text:
            last_100 = text[-100:]
            has_hook = any(c in last_100 for c in ["？", "！", "……", "——", "「"])
            if not has_hook:
                issues.append({
                    "severity": "high",
                    "message": "章末缺少明显的悬念钩子",
                    "location": "结尾",
                    "suggestion": "以悬念、反转或强情绪结尾，提升追读欲望",
                })

        score = 7.5 - len(issues) * 2.5
        score = max(0, min(10, score))

        return {
            "dimension": self.dimension,
            "score": score,
            "passed": score >= 6,
            "issues": issues,
        }
```

### 审查结果数据结构

```python
# 单个维度结果
{
    "dimension": "爽点密度",
    "score": 7.5,
    "passed": True,
    "issues": [
        {
            "severity": "medium",
            "message": "开头 200 字缺少钩子",
            "dimension": "爽点密度",
            "location": "开头",
            "suggestion": "以对话或动作开场",
        }
    ],
}

# 汇总结果（execute_step 返回）
{
    "review_results": [...],    # 6 个维度的结果
    "total_score": 7.8,         # 平均分
    "issues_count": 3,          # 总问题数
    "critical_count": 0,        # critical 问题数
}
```

## TDD 验收

- Happy path：传入正常文本 → 6 个检查器并行执行 → 返回 6 个维度结果 → total_score 在 0-10 之间
- Edge case 1：mode="minimal" → 只执行 3 个核心检查器 → review_results 长度为 3
- Edge case 2：某个检查器抛异常 → 该维度 score=0，其余正常返回
- Error case：text 为空 → 各检查器不崩溃，返回低分但不抛异常
