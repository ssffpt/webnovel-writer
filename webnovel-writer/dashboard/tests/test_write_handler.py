"""Tests for WriteSkillHandler."""
from __future__ import annotations

import pytest

from dashboard.skill_handlers.write_handler import WriteSkillHandler
from dashboard.skill_models import StepState


@pytest.fixture
def handler():
    return WriteSkillHandler()


class TestGetSteps:
    def test_standard_mode_returns_seven_steps(self, handler):
        steps = handler.get_steps("standard")
        assert len(steps) == 7
        step_ids = [s.id for s in steps]
        assert step_ids == [
            "step_1", "step_2a", "step_2b", "step_3", "step_4", "step_5", "step_6",
        ]

    def test_standard_mode_step_2b_not_skippable(self, handler):
        steps = handler.get_steps("standard")
        step_2b = next(s for s in steps if s.id == "step_2b")
        assert step_2b.skippable is False

    def test_fast_mode_step_2b_skippable(self, handler):
        steps = handler.get_steps("fast")
        step_2b = next(s for s in steps if s.id == "step_2b")
        assert step_2b.skippable is True

    def test_minimal_mode_step_2b_skippable(self, handler):
        steps = handler.get_steps("minimal")
        step_2b = next(s for s in steps if s.id == "step_2b")
        assert step_2b.skippable is True

    def test_fast_and_minimal_other_steps_unchanged(self, handler):
        for mode in ("fast", "minimal"):
            steps = handler.get_steps(mode)
            expected_ids = ["step_1", "step_2a", "step_2b", "step_3", "step_4", "step_5", "step_6"]
            assert [s.id for s in steps] == expected_ids

    def test_default_mode_equals_standard(self, handler):
        default_steps = handler.get_steps()
        standard_steps = handler.get_steps("standard")
        assert [s.id for s in default_steps] == [s.id for s in standard_steps]


class TestValidateInput:
    @pytest.fixture
    def step_2a(self):
        return StepState(step_id="step_2a", status="waiting_input")

    @pytest.fixture
    def step_2b(self):
        return StepState(step_id="step_2b", status="waiting_input")

    @pytest.fixture
    def step_4(self):
        return StepState(step_id="step_4", status="waiting_input")

    # --- Step 2A validation ---

    @pytest.mark.asyncio
    async def test_step_2a_confirmed_ok(self, handler, step_2a):
        result = await handler.validate_input(step_2a, {"confirmed": True})
        assert result is None

    @pytest.mark.asyncio
    async def test_step_2a_not_confirmed_with_edited_text_ok(self, handler, step_2a):
        result = await handler.validate_input(step_2a, {"confirmed": False, "edited_text": "some edited text"})
        assert result is None

    @pytest.mark.asyncio
    async def test_step_2a_not_confirmed_no_edited_text_error(self, handler, step_2a):
        result = await handler.validate_input(step_2a, {"confirmed": False})
        assert result == "请确认草稿或提交修改后的文本"

    @pytest.mark.asyncio
    async def test_step_2a_empty_edited_text_error(self, handler, step_2a):
        result = await handler.validate_input(step_2a, {"confirmed": False, "edited_text": ""})
        assert result == "请确认草稿或提交修改后的文本"

    # --- Step 2B validation ---

    @pytest.mark.asyncio
    async def test_step_2b_confirmed_ok(self, handler, step_2b):
        result = await handler.validate_input(step_2b, {"confirmed": True})
        assert result is None

    @pytest.mark.asyncio
    async def test_step_2b_not_confirmed_with_feedback_ok(self, handler, step_2b):
        result = await handler.validate_input(step_2b, {"confirmed": False, "feedback": "需要调整语气"})
        assert result is None

    @pytest.mark.asyncio
    async def test_step_2b_not_confirmed_no_feedback_error(self, handler, step_2b):
        result = await handler.validate_input(step_2b, {"confirmed": False})
        assert result == "请确认风格适配结果或提出修改意见"

    # --- Step 4 validation ---

    @pytest.mark.asyncio
    async def test_step_4_confirmed_ok(self, handler, step_4):
        result = await handler.validate_input(step_4, {"confirmed": True})
        assert result is None

    @pytest.mark.asyncio
    async def test_step_4_not_confirmed_with_edited_text_ok(self, handler, step_4):
        result = await handler.validate_input(step_4, {"confirmed": False, "edited_text": "润色后的文本"})
        assert result is None

    @pytest.mark.asyncio
    async def test_step_4_not_confirmed_no_edited_text_error(self, handler, step_4):
        result = await handler.validate_input(step_4, {"confirmed": False})
        assert result == "请确认润色结果或提交修改后的文本"


class TestExecuteStep:
    @pytest.mark.asyncio
    async def test_step_1_returns_context_agent_placeholder(self, handler):
        step = StepState(step_id="step_1", status="running")
        result = await handler.execute_step(step, {})
        assert result == {"message": "Context Agent（待实现）"}

    @pytest.mark.asyncio
    async def test_step_3_returns_review_placeholder(self, handler):
        step = StepState(step_id="step_3", status="running")
        result = await handler.execute_step(step, {})
        assert result == {"message": "六维审查（待实现）"}

    @pytest.mark.asyncio
    async def test_step_5_returns_data_agent_placeholder(self, handler):
        step = StepState(step_id="step_5", status="running")
        result = await handler.execute_step(step, {})
        assert result == {"message": "Data Agent（待实现）"}

    @pytest.mark.asyncio
    async def test_step_6_returns_git_backup_placeholder(self, handler):
        step = StepState(step_id="step_6", status="running")
        result = await handler.execute_step(step, {})
        assert result == {"message": "Git 备份（待实现）"}

    @pytest.mark.asyncio
    async def test_unknown_step_returns_empty_dict(self, handler):
        step = StepState(step_id="unknown_step", status="running")
        result = await handler.execute_step(step, {})
        assert result == {}
