"""Tests for PlanSkillHandler Step 6 (chapter outlines) — Task 204."""
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
# Happy path: execute_step step_6 returns chapter_outlines with 16 fields
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_returns_chapter_outlines():
    """Happy path: Step 6 执行后返回 chapter_outlines，数量等于章节范围。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 12,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章事件",
                "emotion_curve": "期待",
                "is_climax": False,
            }
            for i in range(1, 13)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "核心剧情", "chapters": list(range(1, 13))}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "测试总纲",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    assert "chapter_outlines" in result
    outlines = result["chapter_outlines"]
    assert isinstance(outlines, list)
    assert len(outlines) == 12


@pytest.mark.anyio
async def test_execute_step_step6_each_outline_has_16_fields():
    """Edge case 1: 每个 outline 包含全部 16 个字段。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章事件",
                "emotion_curve": "期待",
                "is_climax": False,
            }
            for i in range(1, 5)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "核心剧情", "chapters": list(range(1, 5))}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "测试总纲",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    outlines = result["chapter_outlines"]
    required_fields = [
        "chapter",
        "title",
        "pov",
        "location",
        "time",
        "summary",
        "opening_hook",
        "closing_hook",
        "key_events",
        "character_goals",
        "conflict",
        "emotion_arc",
        "strand",
        "foreshadowing_plant",
        "foreshadowing_reveal",
        "is_climax",
        "word_target",
    ]
    for outline in outlines:
        for field in required_fields:
            assert field in outline, f"Missing field '{field}' in outline {outline.get('chapter')}"


@pytest.mark.anyio
async def test_execute_step_step6_chapter_numbers_correct():
    """Happy path: outline 的 chapter 编号连续递增。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 5,
        "chapter_end": 16,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章事件",
                "emotion_curve": "期待",
                "is_climax": False,
            }
            for i in range(5, 17)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "核心剧情", "chapters": list(range(5, 17))}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "测试总纲",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    outlines = result["chapter_outlines"]
    chapter_numbers = [o["chapter"] for o in outlines]
    assert chapter_numbers == list(range(5, 17))


@pytest.mark.anyio
async def test_execute_step_step6_stores_in_context():
    """Happy path: chapter_outlines 被写入 context。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        "beat_sheet": [
            {"chapter": i, "act": "开端", "event": f"第{i}章", "emotion_curve": "期待", "is_climax": False}
            for i in range(1, 5)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": [1, 2, 3, 4]}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    await handler.execute_step(step, context)

    assert "chapter_outlines" in context
    assert len(context["chapter_outlines"]) == 4


# ---------------------------------------------------------------------------
# Edge case 1: single-chapter volume (no batching needed)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_single_chapter_volume():
    """Edge case 1: 单章卷（chapter_start == chapter_end）→ 只生成 1 章大纲。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 7,
        "chapter_end": 7,
        "beat_sheet": [
            {"chapter": 7, "act": "高潮", "event": "第7章事件", "emotion_curve": "爆发", "is_climax": True}
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": [7]}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    assert len(result["chapter_outlines"]) == 1
    assert result["chapter_outlines"][0]["chapter"] == 7


# ---------------------------------------------------------------------------
# Edge case 2: step.progress increments from 0.0 to 1.0
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_progress_increments():
    """Edge case 2: step.progress 在生成过程中从 0.0 递增到 1.0。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    step.progress = 0.0
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 8,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章",
                "emotion_curve": "期待",
                "is_climax": False,
            }
            for i in range(1, 9)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": list(range(1, 9))}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    await handler.execute_step(step, context)

    assert step.progress == 1.0


# ---------------------------------------------------------------------------
# Error case: beat_sheet 为空 → 仍能生成模板大纲，不报错
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_empty_beat_sheet_no_error():
    """Error case: beat_sheet 为空 → 仍能生成模板大纲，不报错。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 4,
        "beat_sheet": [],  # intentionally empty
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": [1, 2, 3, 4]}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    assert "chapter_outlines" in result
    assert len(result["chapter_outlines"]) == 4
    # Each outline should still have all required fields
    for outline in result["chapter_outlines"]:
        assert "chapter" in outline
        assert "title" in outline


# ---------------------------------------------------------------------------
# Error case: chapter numbers are unique across outlines
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_chapter_numbers_unique():
    """Error case: 每个 outline 的 chapter 编号唯一（无重复）。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 12,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章",
                "emotion_curve": "期待",
                "is_climax": False,
            }
            for i in range(1, 13)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": list(range(1, 13))}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    outlines = result["chapter_outlines"]
    chapter_numbers = [o["chapter"] for o in outlines]
    assert len(chapter_numbers) == len(set(chapter_numbers)), "Duplicate chapter numbers found"


# ---------------------------------------------------------------------------
# Edge case: total_generated in result
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_total_generated():
    """Happy path: 返回结果包含 total_generated 字段。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 20,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章",
                "emotion_curve": "期待",
                "is_climax": False,
            }
            for i in range(1, 21)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": list(range(1, 21))}],
            "hook_points": [],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    assert "total_generated" in result
    assert result["total_generated"] == 20


# ---------------------------------------------------------------------------
# Edge case: hook_points from skeleton mark is_climax
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step6_hooked_chapter_is_climax():
    """Edge case: volume_skeleton.hook_points 中的章节标记 is_climax=True。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "project_root": ".",
        "chapter_start": 1,
        "chapter_end": 12,
        "beat_sheet": [
            {
                "chapter": i,
                "act": "开端",
                "event": f"第{i}章",
                "emotion_curve": "期待",
                "is_climax": i == 5,
            }
            for i in range(1, 13)
        ],
        "volume_skeleton": {
            "strands": [{"name": "主线", "description": "", "chapters": list(range(1, 13))}],
            "hook_points": [
                {"chapter": 5, "type": "大高潮", "description": "高潮"},
            ],
            "foreshadowing": [],
            "constraint_triggers": [],
        },
        "outline": "",
        "settings": {},
    }

    result = await handler.execute_step(step, context)

    outlines = result["chapter_outlines"]
    climax_outline = next((o for o in outlines if o["chapter"] == 5), None)
    assert climax_outline is not None
    assert climax_outline["is_climax"] is True
    non_climax = next((o for o in outlines if o["chapter"] == 3), None)
    assert non_climax["is_climax"] is False
