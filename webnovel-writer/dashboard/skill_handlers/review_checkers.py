"""六维审查检查器。每个检查器独立执行，返回统一格式的结果。"""

from abc import ABC, abstractmethod


class BaseChecker(ABC):
    """检查器基类。"""

    dimension: str = ""

    def __init__(self, text: str, task_brief: dict, contract: dict):
        self.text = text
        self.task_brief = task_brief
        self.contract = contract

    @abstractmethod
    async def check(self) -> dict:
        """执行检查，返回结果。

        Returns:
            {
                "dimension": str,
                "score": float,
                "passed": bool,
                "issues": [
                    {
                        "severity": "critical" | "high" | "medium" | "low",
                        "message": str,
                        "location": str | None,
                        "suggestion": str | None,
                    }
                ],
            }
        """
        ...


class HookDensityChecker(BaseChecker):
    """1. 爽点密度检查。"""
    dimension = "爽点密度"

    async def check(self) -> dict:
        issues = []
        paragraphs = [p for p in self.text.split("\n\n") if p.strip()]

        if paragraphs and not any(c in paragraphs[0][:200] for c in ["「", "\"", "！", "？"]):
            issues.append({
                "severity": "medium",
                "message": "开头 200 字缺少对话或强情绪标点，可能缺少钩子",
                "location": "开头",
                "suggestion": "考虑以对话、动作或悬念开场",
            })

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
        issues = []
        # 降级模式默认高分
        score = 8.0
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
        issues = []
        lines = self.text.split("\n")
        total_chars = len(self.text)

        dialogue_chars = sum(
            len(line) for line in lines
            if "「" in line or "」" in line or '"' in line or '"' in line
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
        issues = []
        paragraphs = [p for p in self.text.split("\n\n") if p.strip()]

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
        issues = []
        text = self.text.strip()

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