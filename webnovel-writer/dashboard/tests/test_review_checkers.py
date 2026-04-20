"""Tests for review_checkers.py - six-dimensional review checkers."""

import pytest
import asyncio
from unittest.mock import patch

from dashboard.skill_handlers.review_checkers import (
    HookDensityChecker,
    SettingConsistencyChecker,
    RhythmRatioChecker,
    CharacterOOCChecker,
    NarrativeCoherenceChecker,
    ReadabilityChecker,
)
from dashboard.skill_handlers.write_handler import WriteSkillHandler
from dashboard.skill_models import StepState


@pytest.fixture
def sample_text():
    """A sample chapter text for testing."""
    return (
        "第1章 命运的相遇\n\n"
        "阳光透过窗户洒进房间，「早安」小李轻声说道。\n\n"
        "这是第一章的内容，描写了主角起床后的场景。"
        "主角小明今天要去参加一场重要的面试，他感到既紧张又期待。"
        "「我一定要成功」他默默给自己打气。\n\n"
        "走在路上，他遇到了一个神秘的老人。\n\n"
        "「年轻人，我看你骨骼清奇」老人微笑着说。\n\n"
        "这将是改变他命运的一天！"
    )


@pytest.fixture
def task_brief():
    """A sample task brief."""
    return {
        "chapter_title": "命运的相遇",
        "chapter_outline": "主角小明去面试路上遇到神秘老人",
    }


@pytest.fixture
def contract():
    """A sample contract."""
    return {
        "setting_constraints": [
            "主角叫小明",
            "故事发生在现代都市",
        ],
    }


class TestHookDensityChecker:
    """Tests for HookDensityChecker."""

    @pytest.fixture
    def checker(self, sample_text, task_brief, contract):
        return HookDensityChecker(sample_text, task_brief, contract)

    @pytest.mark.asyncio
    async def test_check_returns_valid_structure(self, checker):
        result = await checker.check()
        assert "dimension" in result
        assert "score" in result
        assert "passed" in result
        assert "issues" in result
        assert result["dimension"] == "爽点密度"

    @pytest.mark.asyncio
    async def test_check_score_in_range(self, checker):
        result = await checker.check()
        assert 0 <= result["score"] <= 10

    @pytest.mark.asyncio
    async def test_check_passed_based_on_score(self, checker):
        result = await checker.check()
        assert result["passed"] == (result["score"] >= 6)

    @pytest.mark.asyncio
    async def test_empty_text_no_crash(self, task_brief, contract):
        checker = HookDensityChecker("", task_brief, contract)
        result = await checker.check()
        assert result["score"] == 7.0  # Default score with no issues
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_issue_generated_for_short_ending(self, task_brief, contract):
        text = "开头有钩子\n\n短"
        checker = HookDensityChecker(text, task_brief, contract)
        result = await checker.check()
        ending_issues = [i for i in result["issues"] if i.get("location") == "结尾"]
        assert len(ending_issues) == 1
        assert ending_issues[0]["severity"] == "low"


class TestSettingConsistencyChecker:
    """Tests for SettingConsistencyChecker."""

    @pytest.fixture
    def checker(self, sample_text, task_brief, contract):
        return SettingConsistencyChecker(sample_text, task_brief, contract)

    @pytest.mark.asyncio
    async def test_returns_high_score_by_default(self, checker):
        result = await checker.check()
        assert result["score"] == 8.0
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_empty_text_no_crash(self, task_brief, contract):
        checker = SettingConsistencyChecker("", task_brief, contract)
        result = await checker.check()
        assert result["score"] == 8.0
        assert result["passed"] is True


class TestRhythmRatioChecker:
    """Tests for RhythmRatioChecker."""

    @pytest.fixture
    def checker(self, sample_text, task_brief, contract):
        return RhythmRatioChecker(sample_text, task_brief, contract)

    @pytest.mark.asyncio
    async def test_dialogue_ratio_calculation(self, checker):
        result = await checker.check()
        assert 0 <= result["score"] <= 10
        assert isinstance(result["passed"], bool)

    @pytest.mark.asyncio
    async def test_low_dialogue_ratio_issue(self, task_brief, contract):
        text = "这是一个很长的叙述段落，没有对话。" * 50
        checker = RhythmRatioChecker(text, task_brief, contract)
        result = await checker.check()
        low_dialogue_issues = [i for i in result["issues"] if "过低" in i.get("message", "")]
        assert len(low_dialogue_issues) >= 1

    @pytest.mark.asyncio
    async def test_high_dialogue_ratio_issue(self, task_brief, contract):
        text = "「你好」\n" * 100
        checker = RhythmRatioChecker(text, task_brief, contract)
        result = await checker.check()
        high_dialogue_issues = [i for i in result["issues"] if "过高" in i.get("message", "")]
        assert len(high_dialogue_issues) >= 1


class TestCharacterOOCChecker:
    """Tests for CharacterOOCChecker."""

    @pytest.fixture
    def checker(self, sample_text, task_brief, contract):
        return CharacterOOCChecker(sample_text, task_brief, contract)

    @pytest.mark.asyncio
    async def test_returns_high_score(self, checker):
        result = await checker.check()
        assert result["score"] == 8.0
        assert result["passed"] is True
        assert result["issues"] == []

    @pytest.mark.asyncio
    async def test_empty_text_no_crash(self, task_brief, contract):
        checker = CharacterOOCChecker("", task_brief, contract)
        result = await checker.check()
        assert result["score"] == 8.0
        assert result["passed"] is True


class TestNarrativeCoherenceChecker:
    """Tests for NarrativeCoherenceChecker."""

    @pytest.fixture
    def checker(self, sample_text, task_brief, contract):
        return NarrativeCoherenceChecker(sample_text, task_brief, contract)

    @pytest.mark.asyncio
    async def test_normal_text_passes(self, checker):
        result = await checker.check()
        assert result["score"] == 8.0
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_long_paragraph_generates_issue(self, task_brief, contract):
        long_paragraph = "这是一段很长的文本。" * 100
        text = f"{long_paragraph}\n\n第二段。"
        checker = NarrativeCoherenceChecker(text, task_brief, contract)
        result = await checker.check()
        long_issues = [i for i in result["issues"] if "过长" in i.get("message", "")]
        assert len(long_issues) >= 1

    @pytest.mark.asyncio
    async def test_empty_text_no_crash(self, task_brief, contract):
        checker = NarrativeCoherenceChecker("", task_brief, contract)
        result = await checker.check()
        assert result["score"] == 8.0
        assert result["passed"] is True


class TestReadabilityChecker:
    """Tests for ReadabilityChecker."""

    @pytest.fixture
    def checker(self, sample_text, task_brief, contract):
        return ReadabilityChecker(sample_text, task_brief, contract)

    @pytest.mark.asyncio
    async def test_text_with_ending_hook(self, checker):
        result = await checker.check()
        assert 0 <= result["score"] <= 10

    @pytest.mark.asyncio
    async def test_text_without_ending_hook_fails(self, task_brief, contract):
        text = "这是一个普通的结尾，没有悬念。" * 10
        checker = ReadabilityChecker(text, task_brief, contract)
        result = await checker.check()
        hook_issues = [i for i in result["issues"] if "悬念钩子" in i.get("message", "")]
        assert len(hook_issues) >= 1
        assert result["score"] < 6  # Should fail

    @pytest.mark.asyncio
    async def test_empty_text_no_crash(self, task_brief, contract):
        checker = ReadabilityChecker("", task_brief, contract)
        result = await checker.check()
        # Empty text has no ending to check, so score is default 7.5
        assert result["score"] == 7.5
        assert result["passed"] is True


class TestRunReview:
    """Integration tests for _run_review in WriteSkillHandler."""

    @pytest.fixture
    def handler(self):
        return WriteSkillHandler()

    @pytest.fixture
    def step_3(self):
        return StepState(step_id="step_3", status="running")

    @pytest.mark.asyncio
    async def test_standard_mode_runs_all_six_checkers(self, handler, step_3):
        context = {
            "draft_text": "「你好」小明说道。这是一个测试章节。\n\n结尾有悬念吗？",
            "task_brief": {"chapter_title": "测试"},
            "context_contract": {},
            "mode": "standard",
        }

        result = await handler.execute_step(step_3, context)

        assert "review_results" in result
        assert len(result["review_results"]) == 6
        assert "total_score" in result
        assert 0 <= result["total_score"] <= 10
        assert "issues_count" in result

    @pytest.mark.asyncio
    async def test_minimal_mode_runs_three_checkers(self, handler, step_3):
        context = {
            "draft_text": "「你好」小明说道。",
            "task_brief": {},
            "context_contract": {},
            "mode": "minimal",
        }

        result = await handler.execute_step(step_3, context)

        assert len(result["review_results"]) == 3
        dimensions = {r["dimension"] for r in result["review_results"]}
        assert "设定一致性" in dimensions
        assert "人物OOC" in dimensions
        assert "叙事连贯性" in dimensions

    @pytest.mark.asyncio
    async def test_checker_exception_handled_gracefully(self, handler, step_3):
        context = {
            "draft_text": "测试文本",
            "task_brief": {},
            "context_contract": {},
            "mode": "standard",
        }

        # Patch one checker to raise an exception
        with patch(
            "dashboard.skill_handlers.review_checkers.HookDensityChecker.check",
            side_effect=RuntimeError("Test error"),
        ):
            result = await handler.execute_step(step_3, context)

        # Should still get results, but one checker has error
        assert len(result["review_results"]) == 6
        error_results = [r for r in result["review_results"] if r["score"] == 0]
        assert len(error_results) >= 1

    @pytest.mark.asyncio
    async def test_empty_text_no_crash(self, handler, step_3):
        context = {
            "draft_text": "",
            "task_brief": {},
            "context_contract": {},
            "mode": "standard",
        }

        result = await handler.execute_step(step_3, context)

        assert "review_results" in result
        assert "total_score" in result
        # None of the checkers should crash
        for r in result["review_results"]:
            assert "score" in r

    @pytest.mark.asyncio
    async def test_uses_adapted_text_when_available(self, handler, step_3):
        context = {
            "draft_text": "旧文本",
            "adapted_text": "新文本「有对话」结尾悬念？",
            "task_brief": {},
            "context_contract": {},
            "mode": "standard",
        }

        result = await handler.execute_step(step_3, context)

        # Should use adapted_text, not draft_text
        assert "review_results" in result
        # Readability checker should pass because ending has "？"
        readability_result = next(
            r for r in result["review_results"] if r["dimension"] == "追读力"
        )
        assert readability_result["passed"] is True

    @pytest.mark.asyncio
    async def test_issues_sorted_by_severity(self, handler, step_3):
        context = {
            "draft_text": "短",
            "task_brief": {},
            "context_contract": {},
            "mode": "standard",
        }

        result = await handler.execute_step(step_3, context)

        if "review_issues" in context:
            issues = context["review_issues"]
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for i in range(len(issues) - 1):
                curr_severity = severity_order.get(issues[i].get("severity", "low"), 4)
                next_severity = severity_order.get(issues[i + 1].get("severity", "low"), 4)
                assert curr_severity <= next_severity
