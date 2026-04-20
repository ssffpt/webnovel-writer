"""Tests for ReviewSkillHandler — Task 401 TDD."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_models import StepDefinition, StepState


# ---------------------------------------------------------------------------
# Handler import helper
# ---------------------------------------------------------------------------

def _handler():
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    return ReviewSkillHandler


def _registry():
    from dashboard.skill_registry import default_registry
    return default_registry


# ---------------------------------------------------------------------------
# Happy path: registry
# ---------------------------------------------------------------------------

def test_default_registry_has_review_handler():
    """default_registry.get_handler("review") returns ReviewSkillHandler instance."""
    registry = _registry()
    handler = registry.get_handler("review")
    assert handler is not None
    assert isinstance(handler, _handler())


# ---------------------------------------------------------------------------
# Happy path: get_steps
# ---------------------------------------------------------------------------

def test_review_handler_get_steps_returns_8_steps():
    """ReviewSkillHandler.get_steps() returns 8 StepDefinitions."""
    handler = _handler()()
    steps = handler.get_steps()
    assert len(steps) == 8


def test_review_handler_step_ids():
    """Step IDs are step_1 through step_8."""
    handler = _handler()()
    steps = handler.get_steps()
    assert [s.id for s in steps] == [
        "step_1", "step_2", "step_3", "step_4",
        "step_5", "step_6", "step_7", "step_8",
    ]


def test_review_handler_step_names():
    """Step names match the specification."""
    handler = _handler()()
    steps = handler.get_steps()
    assert [s.name for s in steps] == [
        "加载参考",
        "加载项目状态",
        "并行审查",
        "生成审查报告",
        "保存审查指标",
        "写回审查记录",
        "处理关键问题",
        "收尾",
    ]


def test_review_handler_interaction_types():
    """Steps 1-3, 5-6, 8 are auto; steps 4 and 7 are confirm."""
    handler = _handler()()
    steps = handler.get_steps()
    by_id = {s.id: s.interaction for s in steps}
    assert by_id["step_1"] == "auto"
    assert by_id["step_2"] == "auto"
    assert by_id["step_3"] == "auto"
    assert by_id["step_4"] == "confirm"
    assert by_id["step_5"] == "auto"
    assert by_id["step_6"] == "auto"
    assert by_id["step_7"] == "confirm"
    assert by_id["step_8"] == "auto"


# ---------------------------------------------------------------------------
# Happy path: Step 1 — load references
# ---------------------------------------------------------------------------

def test_review_handler_step1_loads_all_references():
    """Step 1 loads core_constraints, creativity_constraints, outline, settings."""
    handler = _handler()()
    context = {"project_root": str(REPO_ROOT)}

    result = asyncio.run(handler._load_references(context))

    assert result["loaded"] is True
    assert "references" in context
    refs = context["references"]
    assert isinstance(refs["core_constraints"], str)
    assert isinstance(refs["creativity_constraints"], list)
    assert isinstance(refs["outline"], str)
    assert isinstance(refs["settings"], dict)


# ---------------------------------------------------------------------------
# Edge case 1: core-constraints.md missing → has_constraints=False
# ---------------------------------------------------------------------------

def test_review_handler_step1_missing_constraints_file():
    """Missing core-constraints.md sets has_constraints=False, does not raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = _handler()()
        context = {"project_root": tmpdir}

        result = asyncio.run(handler._load_references(context))

        assert result["loaded"] is True
        assert result["has_constraints"] is False


# ---------------------------------------------------------------------------
# Edge case 2: state.json / chapter missing → chapters_missing listed
# ---------------------------------------------------------------------------

def test_review_handler_step2_missing_chapters():
    """Non-existent chapters are listed in chapters_missing, not blocking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a empty 正文 dir and .webnovel dir
        zhengwen_dir = Path(tmpdir) / "正文"
        zhengwen_dir.mkdir(parents=True, exist_ok=True)
        webnovel_dir = Path(tmpdir) / ".webnovel"
        webnovel_dir.mkdir(parents=True, exist_ok=True)

        handler = _handler()()
        context = {
            "project_root": tmpdir,
            "chapter_start": 1,
            "chapter_end": 5,
        }

        result = asyncio.run(handler._load_project_state(context))

        assert result["chapters_loaded"] == 0
        assert result["chapters_missing"] == [1, 2, 3, 4, 5]
        assert "review_chapters" in context


# ---------------------------------------------------------------------------
# Error case: state.json malformed → returns empty state, no exception
# ---------------------------------------------------------------------------

def test_review_handler_step2_malformed_state_json():
    """Malformed state.json returns empty dict, does not raise."""
    with tempfile.TemporaryDirectory() as tmpdir:
        webnovel_dir = Path(tmpdir) / ".webnovel"
        webnovel_dir.mkdir(parents=True, exist_ok=True)
        state_path = webnovel_dir / "state.json"
        state_path.write_text("{ invalid json }", encoding="utf-8")

        handler = _handler()()
        context = {"project_root": tmpdir}

        # Must not raise
        result = asyncio.run(handler._load_project_state(context))

        assert result["chapters_loaded"] == 0
        assert context["project_state"] == {}


# ---------------------------------------------------------------------------
# Happy path: Step 2 — loads chapters and outlines
# ---------------------------------------------------------------------------

def test_review_handler_step2_loads_chapters_and_outlines():
    """Step 2 loads existing chapter text and chapter outlines."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 正文 dir with chapter 1 and 3
        zhengwen_dir = Path(tmpdir) / "正文"
        zhengwen_dir.mkdir(parents=True, exist_ok=True)
        (zhengwen_dir / "第1章.md").write_text("第一章正文内容", encoding="utf-8")
        (zhengwen_dir / "第3章.md").write_text("第三章正文内容", encoding="utf-8")

        # Create 大纲 dir with outline for chapter 1
        dagang_dir = Path(tmpdir) / "大纲" / "第一卷"
        dagang_dir.mkdir(parents=True, exist_ok=True)
        outline_data = {"chapter": 1, "title": "第一章"}
        (dagang_dir / "第1章.json").write_text(
            json.dumps(outline_data, ensure_ascii=False), encoding="utf-8"
        )

        handler = _handler()()
        context = {
            "project_root": tmpdir,
            "chapter_start": 1,
            "chapter_end": 3,
        }

        result = asyncio.run(handler._load_project_state(context))

        assert result["chapters_loaded"] == 2
        assert result["chapters_missing"] == [2]
        assert result["has_outlines"] is True
        assert 1 in context["review_chapters"]
        assert context["review_chapters"][1] == "第一章正文内容"
        assert 3 in context["review_chapters"]
        assert context["chapter_outlines"][1] == outline_data


# ---------------------------------------------------------------------------
# validate_input
# ---------------------------------------------------------------------------

def test_validate_input_step4_requires_confirmed():
    """Step 4 validate_input returns error when confirmed is False."""
    handler = _handler()()
    step = StepState(step_id="step_4", status="waiting_input")

    result = asyncio.run(handler.validate_input(step, {"confirmed": False}))
    assert result == "请确认审查报告"

    result_ok = asyncio.run(handler.validate_input(step, {"confirmed": True}))
    assert result_ok is None


def test_validate_input_step7_requires_decisions():
    """Step 7 validate_input returns error when decisions is empty."""
    handler = _handler()()
    step = StepState(step_id="step_7", status="waiting_input")

    result = asyncio.run(handler.validate_input(step, {"decisions": []}))
    assert result == "请对关键问题做出决策"

    result_ok = asyncio.run(handler.validate_input(step, {"decisions": [{"id": 1}]}))
    assert result_ok is None
