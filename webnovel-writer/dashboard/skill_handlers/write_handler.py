"""WriteSkillHandler — 6-step chapter writing workflow."""
from __future__ import annotations

from ..skill_runner import SkillHandler
from ..skill_models import StepDefinition, StepState


class WriteSkillHandler(SkillHandler):
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """Return step list for the given mode.

        mode:
            "standard" (default) — all steps
            "fast" — skip Step 2B (style adaptation)
            "minimal" — skip Step 2B, Step 3 core 3-item review only
        """
        mode = mode or "standard"

        steps = [
            StepDefinition(id="step_1", name="Context Agent", interaction="auto"),
            StepDefinition(id="step_2a", name="正文起草", interaction="confirm"),
            StepDefinition(
                id="step_2b",
                name="风格适配",
                interaction="confirm",
                skippable=(mode in ("fast", "minimal")),
            ),
            StepDefinition(id="step_3", name="六维审查", interaction="auto"),
            StepDefinition(id="step_4", name="润色", interaction="confirm"),
            StepDefinition(id="step_5", name="Data Agent", interaction="auto"),
            StepDefinition(id="step_6", name="Git 备份", interaction="auto"),
        ]

        return steps

    async def execute_step(self, step: StepState, context: dict) -> dict:
        """Execute an auto step. Full implementations come in later tasks."""
        if step.step_id == "step_1":
            from .context_builder import ContextBuilder
            builder = ContextBuilder(context)
            return await builder.build()
        if step.step_id == "step_3":
            return {"message": "六维审查（待实现）"}
        if step.step_id == "step_5":
            return {"message": "Data Agent（待实现）"}
        if step.step_id == "step_6":
            return {"message": "Git 备份（待实现）"}
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """Validate user input for confirm steps."""
        if step.step_id == "step_2a":
            return self._validate_draft_confirm(data)
        if step.step_id == "step_2b":
            return self._validate_style_confirm(data)
        if step.step_id == "step_4":
            return self._validate_polish_confirm(data)
        return None

    def _validate_draft_confirm(self, data: dict) -> str | None:
        """Step 2A confirm: user confirms draft or submits edited text."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            edited_text = data.get("edited_text", "")
            if not edited_text:
                return "请确认草稿或提交修改后的文本"
        return None

    def _validate_style_confirm(self, data: dict) -> str | None:
        """Step 2B confirm: user confirms style adaptation result."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            feedback = data.get("feedback", "")
            if not feedback:
                return "请确认风格适配结果或提出修改意见"
        return None

    def _validate_polish_confirm(self, data: dict) -> str | None:
        """Step 4 confirm: user confirms polish result."""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            edited_text = data.get("edited_text", "")
            if not edited_text:
                return "请确认润色结果或提交修改后的文本"
        return None
