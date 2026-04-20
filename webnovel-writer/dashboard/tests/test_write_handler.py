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
    async def test_step_1_returns_context_agent_result(self, handler):
        step = StepState(step_id="step_1", status="running")
        context = {
            "project_root": "/nonexistent",
            "chapter_num": 1,
            "mode": "standard",
        }
        result = await handler.execute_step(step, context)
        # Now returns real ContextBuilder output
        assert "task_brief" in result
        assert "context_contract" in result
        assert "rag_mode" in result
        assert "instruction" in result

    @pytest.mark.asyncio
    async def test_step_3_returns_review_result(self, handler):
        step = StepState(step_id="step_3", status="running")
        context = {
            "draft_text": "「你好」测试文本。",
            "task_brief": {},
            "context_contract": {},
            "mode": "standard",
        }
        result = await handler.execute_step(step, context)
        assert "review_results" in result
        assert "total_score" in result
        assert len(result["review_results"]) == 6

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


class TestExecuteStep2A:
    """Tests for Step 2A (draft chapter generation)."""

    @pytest.mark.asyncio
    async def test_step_2a_returns_draft_text(self, handler):
        """Happy path: execute_step('step_2a') returns draft_text with word_count > 0."""
        step = StepState(step_id="step_2a", status="running")
        context = {
            "chapter_num": 3,
            "task_brief": {"chapter_outline": "这是一个测试大纲，包含章节的主要情节发展。"},
        }
        result = await handler.execute_step(step, context)

        assert "draft_text" in result
        assert result["word_count"] > 0
        assert "instruction" in result
        # context should be mutated
        assert "draft_text" in context
        assert context["draft_word_count"] > 0

    @pytest.mark.asyncio
    async def test_step_2a_fallback_contains_chapter_number(self, handler):
        """Fallback draft includes the chapter number in heading."""
        step = StepState(step_id="step_2a", status="running")
        context = {
            "chapter_num": 5,
            "task_brief": {"chapter_outline": "测试大纲"},
        }
        result = await handler.execute_step(step, context)

        assert "# 第5章" in result["draft_text"]
        assert "AI 草稿占位" in result["draft_text"]

    @pytest.mark.asyncio
    async def test_step_2a_uses_outline_in_fallback(self, handler):
        """Fallback draft includes outline summary."""
        step = StepState(step_id="step_2a", status="running")
        context = {
            "chapter_num": 1,
            "task_brief": {"chapter_outline": "这是非常长的章节大纲" * 20},
        }
        result = await handler.execute_step(step, context)

        # Should truncate to 200 chars
        assert "大纲摘要：" in result["draft_text"]
        assert "这是非常长的章节大纲" in result["draft_text"]

    @pytest.mark.asyncio
    async def test_step_2a_handles_missing_task_brief(self, handler):
        """Handles missing task_brief gracefully."""
        step = StepState(step_id="step_2a", status="running")
        context = {"chapter_num": 1}
        result = await handler.execute_step(step, context)

        assert "draft_text" in result
        assert result["word_count"] > 0


class TestExecuteStep2B:
    """Tests for Step 2B (style adaptation)."""

    @pytest.mark.asyncio
    async def test_step_2b_fallback_returns_original_text(self, handler):
        """Edge case: in fallback mode, adapted_text == draft_text, has_changes=False."""
        step = StepState(step_id="step_2b", status="running")
        context = {
            "draft_text": "这是原始草稿文本，包含一些内容。",
            "task_brief": {},
        }
        result = await handler.execute_step(step, context)

        assert result["adapted_text"] == context["draft_text"]
        assert result["has_changes"] is False
        assert "无需调整（降级模式）" in result["changes_summary"]

    @pytest.mark.asyncio
    async def test_step_2b_returns_has_changes_and_summary(self, handler):
        """Step 2B returns has_changes flag and changes_summary."""
        step = StepState(step_id="step_2b", status="running")
        context = {
            "draft_text": "原始文本。",
            "task_brief": {"style_reference": "简洁有力的文风"},
        }
        result = await handler.execute_step(step, context)

        assert "adapted_text" in result
        assert "has_changes" in result
        assert "changes_summary" in result
        assert "instruction" in result
        # context should be mutated
        assert "adapted_text" in context

    @pytest.mark.asyncio
    async def test_step_2b_handles_empty_draft_text(self, handler):
        """Handles empty draft_text gracefully."""
        step = StepState(step_id="step_2b", status="running")
        context = {"draft_text": ""}
        result = await handler.execute_step(step, context)

        assert result["adapted_text"] == ""
        assert result["has_changes"] is False
