"""EchoSkillHandler — a simple 3-step test skill."""
from __future__ import annotations

import asyncio

from dashboard.skill_models import StepDefinition, StepState
from dashboard.skill_runner import SkillHandler


class EchoSkillHandler(SkillHandler):
    """Test Skill with 3 steps: prepare → user confirm → complete."""

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="准备", interaction="auto"),
            StepDefinition(id="step_2", name="用户确认", interaction="confirm"),
            StepDefinition(id="step_3", name="完成", interaction="auto"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        if step.step_id == "step_1":
            await asyncio.sleep(0.1)
            return {"message": "准备完成"}

        if step.step_id == "step_2":
            # step_2 is a confirm step; execute_step is called after
            # submit_input validates the input. Return the user's data.
            return step.input_data or {}

        if step.step_id == "step_3":
            await asyncio.sleep(0.1)
            return {"message": "echo 完成", "echo": context}

        raise ValueError(f"unknown step_id: {step.step_id}")

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        if not data:
            return "输入数据不能为空"
        return None
