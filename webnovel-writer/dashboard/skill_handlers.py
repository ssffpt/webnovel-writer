"""SkillHandler implementations — EchoSkillHandler for Phase 0 testing."""
from __future__ import annotations

import asyncio

from dashboard.skill_runner import SkillHandler, StepDefinition


class EchoSkillHandler(SkillHandler):
    """Test Skill with 3 steps: auto -> confirm -> auto.

    Step 1 (auto):     sleep 0.1s, returns {"message": "准备完成"}
    Step 2 (confirm):  waits for user input, returns user data
    Step 3 (auto):     sleep 0.1s, returns {"message": "echo 完成", "echo": context}
    """

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="准备", interaction="auto"),
            StepDefinition(id="step_2", name="用户确认", interaction="confirm"),
            StepDefinition(id="step_3", name="完成", interaction="auto"),
        ]

    async def execute_step(self, step, context: dict) -> dict:
        if step.step_id == "step_1":
            await asyncio.sleep(0.1)
            return {"message": "准备完成"}
        if step.step_id == "step_2":
            return {"message": "用户已确认", "confirmed": True}
        if step.step_id == "step_3":
            await asyncio.sleep(0.1)
            return {"message": "echo 完成", "echo": context}
        return {}

    async def validate_input(self, step, data: dict) -> str | None:
        if step.step_id == "step_2":
            if not data:
                return "确认数据不能为空"
        return None


class _InitSkillHandlerPlaceholder(SkillHandler):
    """Deprecated — use dashboard.skill_handlers.init_handler.InitSkillHandler."""

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="初始化", interaction="auto"),
        ]

    async def execute_step(self, step, context: dict) -> dict:
        return {"message": "初始化完成"}

    async def validate_input(self, step, data: dict) -> str | None:
        return None


class PlanSkillHandler(SkillHandler):
    """Plan Skill — placeholder for future implementation."""

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="规划", interaction="auto"),
        ]

    async def execute_step(self, step, context: dict) -> dict:
        return {"message": "规划完成"}

    async def validate_input(self, step, data: dict) -> str | None:
        return None


class WriteSkillHandler(SkillHandler):
    """Write Skill — placeholder for future implementation."""

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="写作", interaction="auto"),
        ]

    async def execute_step(self, step, context: dict) -> dict:
        return {"message": "写作完成"}

    async def validate_input(self, step, data: dict) -> str | None:
        return None
