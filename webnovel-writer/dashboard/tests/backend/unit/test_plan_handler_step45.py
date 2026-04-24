"""Tests for PlanSkillHandler Step 4 (beat table) and Step 4.5 (timeline) — Task 202."""
from __future__ import annotations

import asyncio
import sys
import tempfile
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
# Happy path: Step 4 — execute_step returns beat_sheet
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step4_returns_beat_sheet():
    """Happy path: Step 4 执行后返回 beats 列表，每个 beat 有 chapter/act/event/emotion_curve。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="running")
    context = {
        "project_root": ".",
        "volume_name": "第一卷·初入江湖",
        "chapter_start": 1,
        "chapter_end": 12,
        "volume_theme": "成长",
        "outline": "# 测试大纲\n",
        "idea_bank": {},
    }

    result = await handler.execute_step(step, context)

    assert "beats" in result
    assert "instruction" in result
    beats = result["beats"]
    assert isinstance(beats, list)
    assert len(beats) == 12  # 12 chapters
    # Check first beat structure
    first = beats[0]
    assert "chapter" in first
    assert "act" in first
    assert "event" in first
    assert "emotion_curve" in first
    assert first["chapter"] == 1
    # Verify three-act structure: 12 chapters → act1=3, act2=6, act3=3
    act_counts = {}
    for b in beats:
        act_counts[b["act"]] = act_counts.get(b["act"], 0) + 1
    assert act_counts.get("开端") == 3
    assert act_counts.get("发展") == 6
    assert act_counts.get("高潮") == 3


@pytest.mark.anyio
async def test_execute_step_step4_stores_beat_sheet_in_context():
    """Happy path: beat_sheet 被写入 context。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="running")
    context = {
        "project_root": ".",
        "volume_name": "第一卷",
        "chapter_start": 5,
        "chapter_end": 10,  # 6 chapters
        "volume_theme": "",
        "outline": "",
        "idea_bank": {},
    }

    await handler.execute_step(step, context)

    assert "beat_sheet" in context
    assert len(context["beat_sheet"]) == 6


@pytest.mark.anyio
async def test_execute_step_step4_edge_case_missing_volume_name():
    """Edge case 1: context 缺少 volume_name → 返回降级节拍表，不报错。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 8,
        "volume_theme": "",
        "outline": "",
        "idea_bank": {},
        # volume_name intentionally missing
    }

    result = await handler.execute_step(step, context)

    assert "beats" in result
    assert len(result["beats"]) == 8
    # Still has required fields
    for beat in result["beats"]:
        assert "chapter" in beat
        assert "act" in beat
        assert "event" in beat
        assert "emotion_curve" in beat


# ---------------------------------------------------------------------------
# Happy path: Step 4.5 — execute_step returns timeline
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step4_5_returns_timeline():
    """Happy path: Step 4.5 执行后返回 timeline，每个事件有 day/chapter/strand。"""
    handler = _handler()()
    step = StepState(step_id="step_4_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 12,
        "beat_sheet": [
            {"chapter": 1, "act": "开端", "event": "第1章事件", "emotion_curve": "期待"},
            {"chapter": 2, "act": "开端", "event": "第2章事件", "emotion_curve": "期待"},
            {"chapter": 3, "act": "高潮", "event": "第3章事件", "emotion_curve": "爆发"},
        ],
    }

    result = await handler.execute_step(step, context)

    assert "timeline" in result
    assert "instruction" in result
    timeline = result["timeline"]
    assert isinstance(timeline, list)
    assert len(timeline) == 3
    # Each event has required fields
    for evt in timeline:
        assert "day" in evt
        assert "chapter" in evt
        assert "strand" in evt


@pytest.mark.anyio
async def test_execute_step_step4_5_stores_timeline_in_context():
    """Happy path: timeline 被写入 context。"""
    handler = _handler()()
    step = StepState(step_id="step_4_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        "beat_sheet": [
            {"chapter": i, "act": "发展", "event": f"第{i}章事件", "emotion_curve": "紧张"}
            for i in range(1, 5)
        ],
    }

    await handler.execute_step(step, context)

    assert "timeline" in context
    assert len(context["timeline"]) == 4


# ---------------------------------------------------------------------------
# Edge case: Step 4.5 without beat_sheet uses fallback
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step4_5_fallback_without_beat_sheet():
    """Edge case 2: context 缺少 beat_sheet → 基于章节数生成 timeline，不报错。"""
    handler = _handler()()
    step = StepState(step_id="step_4_5", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        # beat_sheet intentionally missing
    }

    result = await handler.execute_step(step, context)

    assert "timeline" in result
    assert len(result["timeline"]) == 4
    for evt in result["timeline"]:
        assert "day" in evt
        assert "chapter" in evt
        assert "strand" in evt


# ---------------------------------------------------------------------------
# validate_input Step 4 — confirmed=True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_input_step4_confirmed_true_returns_none():
    """Happy path: validate_input Step 4 收到 confirmed=True → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="waiting_input")
    data = {"confirmed": True}

    result = await handler.validate_input(step, data)

    assert result is None


# ---------------------------------------------------------------------------
# validate_input Step 4 — confirmed=False with feedback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_input_step4_confirmed_false_with_feedback_returns_none():
    """Happy path: validate_input Step 4 收到 confirmed=False 且有 feedback → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="waiting_input")
    data = {"confirmed": False, "feedback": "希望增加感情线节拍"}

    result = await handler.validate_input(step, data)

    assert result is None


# ---------------------------------------------------------------------------
# Error case: validate_input Step 4 — confirmed=False without feedback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_input_step4_confirmed_false_without_feedback_returns_error():
    """Error case: validate_input Step 4 收到 confirmed=False 且无 feedback → 返回错误信息。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="waiting_input")
    data = {"confirmed": False}  # no feedback

    result = await handler.validate_input(step, data)

    assert result is not None
    assert "节拍表" in result


# ---------------------------------------------------------------------------
# validate_input Step 4.5 — confirmed=True
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_input_step4_5_confirmed_true_returns_none():
    """Happy path: validate_input Step 4.5 收到 confirmed=True → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_4_5", status="waiting_input")
    data = {"confirmed": True}

    result = await handler.validate_input(step, data)

    assert result is None


# ---------------------------------------------------------------------------
# Error case: validate_input Step 4.5 — confirmed=False without feedback
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_validate_input_step4_5_confirmed_false_without_feedback_returns_error():
    """Error case: validate_input Step 4.5 收到 confirmed=False 且无 feedback → 返回错误信息。"""
    handler = _handler()()
    step = StepState(step_id="step_4_5", status="waiting_input")
    data = {"confirmed": False}  # no feedback

    result = await handler.validate_input(step, data)

    assert result is not None
    assert "时间线" in result
