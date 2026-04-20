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
    assert result == "请对每个关键问题做出决策"

    result_ok = asyncio.run(handler.validate_input(step, {"decisions": [{"option_id": "auto_fix", "issue": {}}]}))
    assert result_ok is None


def test_validate_input_step7_invalid_option_id():
    """Step 7 validate_input returns error for invalid option_id."""
    handler = _handler()()
    step = StepState(step_id="step_7", status="waiting_input")

    result = asyncio.run(handler.validate_input(step, {"decisions": [{"option_id": "invalid_option", "issue": {}}]}))
    assert result == "无效的修复方案：invalid_option"


def test_validate_input_step7_stores_decisions():
    """Step 7 validate_input stores decisions in handler instance."""
    handler = _handler()()
    step = StepState(step_id="step_7", status="waiting_input")

    decisions = [{"option_id": "auto_fix", "issue": {"message": "test"}}, {"option_id": "ignore", "issue": {}}]
    asyncio.run(handler.validate_input(step, {"decisions": decisions}))

    assert hasattr(handler, '_critical_decisions')
    assert handler._critical_decisions == decisions


# ---------------------------------------------------------------------------
# Happy path: Step 3 — 3 chapters → 6 dimensions each → all_chapter_results
# ---------------------------------------------------------------------------

def test_review_handler_step3_parallel_review_happy_path():
    """3 chapters, each runs 6 dimension checkers in parallel.

    all_chapter_results has 3 keys (one per chapter), each with 6 dimension results.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        zhengwen_dir = Path(tmpdir) / "正文"
        zhengwen_dir.mkdir(parents=True, exist_ok=True)
        (zhengwen_dir / "第1章.md").write_text("第一章正文内容", encoding="utf-8")
        (zhengwen_dir / "第2章.md").write_text("第二章正文内容", encoding="utf-8")
        (zhengwen_dir / "第3章.md").write_text("第三章正文内容", encoding="utf-8")

        handler = _handler()()
        context = {
            "project_root": tmpdir,
            "chapter_start": 1,
            "chapter_end": 3,
        }

        # Step 1 and 2 must run first to populate context
        asyncio.run(handler._load_references(context))
        asyncio.run(handler._load_project_state(context))

        step = StepState(step_id="step_3", status="running")

        result = asyncio.run(handler.execute_step(step, context))

        assert "all_chapter_results" in result
        assert "summary" in result
        all_results = result["all_chapter_results"]
        assert len(all_results) == 3
        assert set(all_results.keys()) == {1, 2, 3}
        for ch_num in (1, 2, 3):
            assert len(all_results[ch_num]) == 6
            dims = {r["dimension"] for r in all_results[ch_num]}
            assert "爽点密度" in dims
            assert "设定一致性" in dims
            assert "节奏比例" in dims
            assert "人物OOC" in dims
            assert "叙事连贯性" in dims
            assert "追读力" in dims


# ---------------------------------------------------------------------------
# Edge case 1: Single chapter review → only 1 key in all_chapter_results
# ---------------------------------------------------------------------------

def test_review_handler_step3_single_chapter():
    """Single chapter review: all_chapter_results has 1 key, progress=1.0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zhengwen_dir = Path(tmpdir) / "正文"
        zhengwen_dir.mkdir(parents=True, exist_ok=True)
        (zhengwen_dir / "第5章.md").write_text("单章内容", encoding="utf-8")

        handler = _handler()()
        context = {
            "project_root": tmpdir,
            "chapter_start": 5,
            "chapter_end": 5,
        }

        asyncio.run(handler._load_references(context))
        asyncio.run(handler._load_project_state(context))

        step = StepState(step_id="step_3", status="running")

        result = asyncio.run(handler.execute_step(step, context))

        assert len(result["all_chapter_results"]) == 1
        assert 5 in result["all_chapter_results"]
        assert step.progress == 1.0


# ---------------------------------------------------------------------------
# Edge case 2: One checker throws exception → its dimension score=0, others OK
# ---------------------------------------------------------------------------

class FailingChecker:
    """A checker that always raises an exception."""
    dimension = "failing_dimension"

    def __init__(self, text, task_brief, contract):
        self.text = text
        self.task_brief = task_brief
        self.contract = contract

    async def check(self):
        raise RuntimeError("checker error")


def test_review_handler_step3_checker_exception_isolation(monkeypatch):
    """One checker raising an exception leaves others intact; failed gets score=0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zhengwen_dir = Path(tmpdir) / "正文"
        zhengwen_dir.mkdir(parents=True, exist_ok=True)
        (zhengwen_dir / "第1章.md").write_text("内容", encoding="utf-8")

        handler = _handler()()
        context = {
            "project_root": tmpdir,
            "chapter_start": 1,
            "chapter_end": 1,
        }

        asyncio.run(handler._load_references(context))
        asyncio.run(handler._load_project_state(context))

        # Monkey-patch HookDensityChecker to fail
        from dashboard.skill_handlers import review_checkers as rc
        original = rc.HookDensityChecker
        rc.HookDensityChecker = FailingChecker

        try:
            step = StepState(step_id="step_3", status="running")
            result = asyncio.run(handler.execute_step(step, context))

            ch1_results = result["all_chapter_results"][1]
            # Find the failing dimension
            failing = next(r for r in ch1_results if r["dimension"] == "failing_dimension")
            assert failing["score"] == 0
            assert not failing["passed"]
            assert any(i["severity"] == "error" for i in failing["issues"])

            # Others should still be present (5 remaining)
            non_failing = [r for r in ch1_results if r["dimension"] != "failing_dimension"]
            assert len(non_failing) == 5
            for r in non_failing:
                assert r["score"] > 0
        finally:
            rc.HookDensityChecker = original


# ---------------------------------------------------------------------------
# Error case: Empty review_chapters → returns empty results, no exception
# ---------------------------------------------------------------------------

def test_review_handler_step3_empty_chapters():
    """review_chapters empty → returns empty all_chapter_results, no exception."""
    handler = _handler()()
    context = {
        "project_root": str(REPO_ROOT),
        "review_chapters": {},
    }
    context["references"] = {
        "core_constraints": "",
        "creativity_constraints": [],
        "settings": {},
    }

    step = StepState(step_id="step_3", status="running")

    result = asyncio.run(handler.execute_step(step, context))

    assert result["all_chapter_results"] == {}
    assert result["summary"]["avg_score"] == 0
    assert result["summary"]["total_issues"] == 0


# ---------------------------------------------------------------------------
# Step 7: Handle critical issues
# ---------------------------------------------------------------------------

def test_review_handler_step7_no_critical_auto_resolved():
    """Step 7 with no critical issues → auto_resolved=True."""
    handler = _handler()()
    context = {
        "review_summary": {"critical_issues": []},
    }

    step = StepState(step_id="step_7", status="running")
    result = asyncio.run(handler.execute_step(step, context))

    assert result["has_critical"] is False
    assert result["auto_resolved"] is True
    assert "无关键问题" in result["instruction"]


def test_review_handler_step7_with_critical_requires_input():
    """Step 7 with critical issues → requires_input=True, returns options."""
    handler = _handler()()
    critical_issues = [
        {"severity": "critical", "message": "矛盾一", "chapter": 1},
        {"severity": "critical", "message": "矛盾二", "chapter": 2},
    ]
    context = {
        "review_summary": {"critical_issues": critical_issues},
    }

    step = StepState(step_id="step_7", status="running")
    result = asyncio.run(handler.execute_step(step, context))

    assert result["has_critical"] is True
    assert result["auto_resolved"] is False
    assert result["requires_input"] is True
    assert len(result["issues_with_options"]) == 2
    assert "发现 2 个关键问题" in result["instruction"]


def test_review_handler_step7_generate_fix_options():
    """Step 7 _generate_fix_options returns 3 options for each issue."""
    handler = _handler()()
    issue = {"severity": "critical", "message": "测试问题"}
    options = handler._generate_fix_options(issue)

    assert len(options) == 3
    ids = {o["id"] for o in options}
    assert ids == {"auto_fix", "ignore", "manual"}
    assert any(o["label"] == "AI 自动修复" for o in options)
    assert any(o["id"] == "auto_fix" for o in options)


# ---------------------------------------------------------------------------
# Step 8: Finalize
# ---------------------------------------------------------------------------

def test_review_handler_step8_saves_report_file():
    """Step 8 saves review report to .webnovel/审查报告/ directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = _handler()()
        context = {
            "project_root": tmpdir,
            "chapter_start": 1,
            "chapter_end": 3,
            "review_report": {"overall": {"avg_score": 8.5}},
        }

        step = StepState(step_id="step_8", status="running")
        result = asyncio.run(handler.execute_step(step, context))

        assert "report_saved" in result
        report_path = Path(result["report_saved"])
        assert report_path.exists()
        assert report_path.parent.name == "审查报告"
        report_data = json.loads(report_path.read_text(encoding="utf-8"))
        assert report_data["overall"]["avg_score"] == 8.5


def test_review_handler_step8_manual_todos_written():
    """Step 8 with manual decisions writes review_todos.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        webnovel_dir = Path(tmpdir) / ".webnovel"
        webnovel_dir.mkdir(parents=True, exist_ok=True)

        handler = _handler()()
        # Pre-set _critical_decisions via validate_input
        decisions = [
            {"option_id": "auto_fix", "issue": {"message": "问题1"}},
            {"option_id": "manual", "issue": {"message": "问题2"}},
        ]
        asyncio.run(handler.validate_input(
            StepState(step_id="step_7", status="waiting_input"),
            {"decisions": decisions}
        ))

        context = {
            "project_root": tmpdir,
            "chapter_start": 1,
            "chapter_end": 1,
            "review_report": {},
        }

        step = StepState(step_id="step_8", status="running")
        result = asyncio.run(handler.execute_step(step, context))

        assert result["manual_todos"] == 1
        todo_path = webnovel_dir / "review_todos.json"
        assert todo_path.exists()
        todos = json.loads(todo_path.read_text(encoding="utf-8"))
        assert len(todos) == 1
        assert todos[0]["message"] == "问题2"
