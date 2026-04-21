"""Tests for PlanSkillHandler Step 5 (volume skeleton) — Task 203."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_models import StepDefinition, StepState


def _handler():
    from dashboard.skill_handlers.plan_handler import PlanSkillHandler
    return PlanSkillHandler


# ---------------------------------------------------------------------------
# Happy path: execute_step step_5 returns skeleton with required keys
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step5_returns_skeleton():
    """Happy path: Step 5 执行后返回 skeleton，skeleton 包含 strands/hook_points/foreshadowing/constraint_triggers。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 12,
        "beat_sheet": [
            {"chapter": 1, "act": "开端", "event": "第1章事件", "emotion_curve": "期待"},
            {"chapter": 2, "act": "开端", "event": "第2章事件", "emotion_curve": "期待"},
            {"chapter": 3, "act": "高潮", "event": "第3章事件", "emotion_curve": "爆发"},
        ],
        "timeline": [
            {"day": 1, "chapter": 1, "strand": "主线"},
            {"day": 2, "chapter": 2, "strand": "主线"},
            {"day": 3, "chapter": 3, "strand": "主线"},
        ],
        "idea_bank": {},
    }

    result = await handler.execute_step(step, context)

    assert "skeleton" in result
    assert "instruction" in result
    skeleton = result["skeleton"]
    assert "strands" in skeleton
    assert "hook_points" in skeleton
    assert "foreshadowing" in skeleton
    assert "constraint_triggers" in skeleton


@pytest.mark.anyio
async def test_execute_step_step5_stores_skeleton_in_context():
    """Happy path: skeleton 被写入 context。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        "beat_sheet": [
            {"chapter": i, "act": "开端", "event": f"第{i}章事件", "emotion_curve": "期待"}
            for i in range(1, 5)
        ],
        "timeline": [
            {"day": i, "chapter": i, "strand": "主线"}
            for i in range(1, 5)
        ],
        "idea_bank": {},
    }

    await handler.execute_step(step, context)

    assert "volume_skeleton" in context
    assert "strands" in context["volume_skeleton"]


# ---------------------------------------------------------------------------
# Edge case 1: context 缺少 beat_sheet → 使用默认结构，不报错
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step5_edge_case_missing_beat_sheet():
    """Edge case 1: context 缺少 beat_sheet → 使用默认结构，不报错。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 8,
        # beat_sheet intentionally missing
        "timeline": [
            {"day": 1, "chapter": 1, "strand": "主线"},
            {"day": 2, "chapter": 2, "strand": "主线"},
        ],
        "idea_bank": {},
    }

    result = await handler.execute_step(step, context)

    assert "skeleton" in result
    skeleton = result["skeleton"]
    assert "strands" in skeleton
    assert "hook_points" in skeleton
    assert "foreshadowing" in skeleton
    assert "constraint_triggers" in skeleton


# ---------------------------------------------------------------------------
# Edge case 2: skeleton 结构完整，每个 strand 有 name/chapters
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step5_strand_structure():
    """Edge case 2: skeleton.strands 每个元素有 name/description/chapters。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 3,
        "chapter_end": 14,  # 12 chapters
        "beat_sheet": [
            {"chapter": i, "act": "开端", "event": f"第{i}章事件", "emotion_curve": "期待"}
            for i in range(3, 15)
        ],
        "timeline": [
            {"day": i, "chapter": i, "strand": "主线"}
            for i in range(3, 15)
        ],
        "idea_bank": {},
    }

    result = await handler.execute_step(step, context)

    skeleton = result["skeleton"]
    strands = skeleton["strands"]
    assert isinstance(strands, list)
    assert len(strands) > 0
    for strand in strands:
        assert "name" in strand
        assert "description" in strand
        assert "chapters" in strand


# ---------------------------------------------------------------------------
# Edge case: idea_bank 无 constraints → constraint_triggers 为空列表，不报错
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step5_empty_idea_bank_constraints():
    """Edge case: idea_bank 无 constraints → constraint_triggers 为空列表，不报错。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        "beat_sheet": [
            {"chapter": i, "act": "开端", "event": f"第{i}章事件", "emotion_curve": "期待"}
            for i in range(1, 5)
        ],
        "timeline": [
            {"day": i, "chapter": i, "strand": "主线"}
            for i in range(1, 5)
        ],
        "idea_bank": {},  # No creativity_package.constraints
    }

    result = await handler.execute_step(step, context)

    skeleton = result["skeleton"]
    assert "constraint_triggers" in skeleton
    assert skeleton["constraint_triggers"] == []


# ---------------------------------------------------------------------------
# Happy path: validate_input step_5 confirmed=True
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_validate_input_step5_confirmed_true_returns_none():
    """Happy path: validate_input Step 5 收到 confirmed=True → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="waiting_input")
    data = {"confirmed": True}

    result = await handler.validate_input(step, data)

    assert result is None


# ---------------------------------------------------------------------------
# Happy path: validate_input step_5 confirmed=False with feedback
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_validate_input_step5_confirmed_false_with_feedback_returns_none():
    """Happy path: validate_input Step 5 收到 confirmed=False 且有 feedback → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="waiting_input")
    data = {"confirmed": False, "feedback": "希望增加感情线比例"}

    result = await handler.validate_input(step, data)

    assert result is None


# ---------------------------------------------------------------------------
# Error case: validate_input step_5 confirmed=False without feedback
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_validate_input_step5_confirmed_false_without_feedback_returns_error():
    """Error case: validate_input Step 5 收到 confirmed=False 且无 feedback → 返回错误信息。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="waiting_input")
    data = {"confirmed": False}  # no feedback

    result = await handler.validate_input(step, data)

    assert result is not None
    assert "卷骨架" in result or "骨架" in result
