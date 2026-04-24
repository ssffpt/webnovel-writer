"""Tests for PlanSkillHandler — TDD for Task 201."""
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


# ---------------------------------------------------------------------------
# Deferred imports
# ---------------------------------------------------------------------------

def _handler():
    from dashboard.skill_handlers.plan_handler import PlanSkillHandler
    return PlanSkillHandler


def _registry():
    from dashboard.skill_registry import default_registry
    return default_registry


# ---------------------------------------------------------------------------
# Happy path: registry → handler → steps
# ---------------------------------------------------------------------------

def test_default_registry_has_plan_handler():
    """default_registry.get_handler("plan") 返回 PlanSkillHandler 实例。"""
    registry = _registry()
    handler = registry.get_handler("plan")
    assert handler is not None
    PlanHandler = _handler()
    assert isinstance(handler, PlanHandler)


def test_plan_handler_get_steps_returns_9_steps():
    """PlanSkillHandler.get_steps() 返回 9 个 StepDefinition。"""
    handler = _handler()()
    steps = handler.get_steps()
    assert len(steps) == 9
    assert [s.id for s in steps] == [
        "step_1", "step_2", "step_3", "step_4", "step_4_5",
        "step_5", "step_6", "step_7", "step_8",
    ]


def test_plan_handler_step_names():
    """每个 step 的 name 与规格一致。"""
    handler = _handler()()
    steps = handler.get_steps()
    names = [s.name for s in steps]
    assert names == [
        "加载项目数据",
        "构建设定基线",
        "选择卷",
        "生成卷节拍表",
        "生成卷时间线表",
        "生成卷骨架",
        "生成章节大纲",
        "回写设定集",
        "验证与保存",
    ]


# ---------------------------------------------------------------------------
# Edge case: interaction 类型
# ---------------------------------------------------------------------------

def test_plan_handler_interaction_types():
    """Step 1-2 是 auto，Step 3 是 form，Step 4-5 是 confirm，Step 6-8 是 auto。"""
    handler = _handler()()
    steps = handler.get_steps()
    interactions = [s.interaction for s in steps]
    assert interactions == [
        "auto", "auto", "form", "confirm", "confirm",
        "confirm", "auto", "auto", "auto",
    ]


# ---------------------------------------------------------------------------
# Step 1: _load_project_data
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step1_loads_from_empty_directory():
    """Edge case 1: 项目目录为空 → 返回空数据但不报错（loaded=True, volumes_count=0）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = _handler()()
        step = StepState(step_id="step_1", status="running")
        context = {"project_root": tmpdir}

        result = await handler.execute_step(step, context)

        assert result["loaded"] is True
        assert result["volumes_count"] == 0
        assert result["has_outline"] is False
        assert result["settings_count"] == 0
        assert "instruction" in result
        # context should be populated
        assert context["state"] == {}
        assert context["settings"] == {}
        assert context["existing_volumes"] == []


@pytest.mark.anyio
async def test_execute_step_step1_loads_existing_volumes():
    """Happy path: 大纲目录包含已有卷 → 正确计数和列表。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create volume directories
        outline_dir = Path(tmpdir) / "大纲"
        outline_dir.mkdir()
        (outline_dir / "第1卷·开篇").mkdir()
        (outline_dir / "第2卷·成长").mkdir()

        handler = _handler()()
        step = StepState(step_id="step_1", status="running")
        context = {"project_root": tmpdir}

        result = await handler.execute_step(step, context)

        assert result["loaded"] is True
        assert result["volumes_count"] == 2
        assert "第1卷·开篇" in context["existing_volumes"]
        assert "第2卷·成长" in context["existing_volumes"]
        assert result["instruction"] == "项目数据加载完成，已有 2 卷"


@pytest.mark.anyio
async def test_execute_step_step1_loads_state_json():
    """Happy path: 存在 state.json → 正确加载到 context。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        webnovel_dir = Path(tmpdir) / ".webnovel"
        webnovel_dir.mkdir()
        state_file = webnovel_dir / "state.json"
        state_file.write_text('{"title": "测试书", "word_count": 10000}', encoding="utf-8")

        handler = _handler()()
        step = StepState(step_id="step_1", status="running")
        context = {"project_root": tmpdir}

        result = await handler.execute_step(step, context)

        assert result["loaded"] is True
        assert context["state"]["title"] == "测试书"
        assert context["state"]["word_count"] == 10000


# ---------------------------------------------------------------------------
# Step 2: _build_setting_baseline
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step2_creates_missing_setting_templates():
    """Happy path: 设定目录为空 → 自动创建缺失的设定模板文件。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        handler = _handler()()
        step = StepState(step_id="step_2", status="running")
        context = {"project_root": tmpdir}

        result = await handler.execute_step(step, context)

        assert result["baseline_ready"] is True
        assert len(result["missing_created"]) == 3
        assert "力量体系.md" in result["missing_created"]
        assert "世界观.md" in result["missing_created"]
        assert "主要角色.md" in result["missing_created"]
        setting_dir = Path(tmpdir) / "设定集"
        assert (setting_dir / "力量体系.md").exists()
        assert (setting_dir / "世界观.md").exists()
        assert (setting_dir / "主要角色.md").exists()


@pytest.mark.anyio
async def test_execute_step_step2_idempotent_when_files_exist():
    """Edge case 2: 设定文件已存在 → 不创建新文件，missing_created 为空。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        setting_dir = Path(tmpdir) / "设定集"
        setting_dir.mkdir()
        (setting_dir / "力量体系.md").write_text("# 炼气筑基\n", encoding="utf-8")
        (setting_dir / "世界观.md").write_text("# 世界观\n", encoding="utf-8")
        # 主要角色.md missing

        handler = _handler()()
        step = StepState(step_id="step_2", status="running")
        context = {"project_root": tmpdir}

        result = await handler.execute_step(step, context)

        assert result["baseline_ready"] is True
        assert len(result["missing_created"]) == 1
        assert "主要角色.md" in result["missing_created"]
        assert result["instruction"] == "已创建缺失设定模板：主要角色.md"


# ---------------------------------------------------------------------------
# Step 3: _validate_volume_selection
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_validate_input_step3_missing_volume_name_returns_error():
    """Edge case: Step 3 缺少 volume_name → 返回 "卷名不能为空"。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {"chapter_start": 1, "chapter_end": 10}

    result = await handler.validate_input(step, data)

    assert result == "卷名不能为空"


@pytest.mark.anyio
async def test_validate_input_step3_missing_chapter_range_returns_error():
    """Edge case: Step 3 缺少章节范围 → 返回 "请指定章节范围"。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {"volume_name": "第一卷"}

    result = await handler.validate_input(step, data)

    assert result == "请指定章节范围（起始章和结束章）"


@pytest.mark.anyio
async def test_validate_input_step3_invalid_chapter_range_returns_error():
    """Error case: Step 3 chapter_start >= chapter_end → 返回 "起始章必须小于结束章"。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {"volume_name": "第一卷", "chapter_start": 10, "chapter_end": 5}

    result = await handler.validate_input(step, data)

    assert result == "起始章必须小于结束章"


@pytest.mark.anyio
async def test_validate_input_step3_chapter_range_too_large_returns_error():
    """Error case: Step 3 章节数超过 50 → 返回 "单卷章节数不宜超过 50 章"。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {"volume_name": "第一卷", "chapter_start": 1, "chapter_end": 100}

    result = await handler.validate_input(step, data)

    assert result == "单卷章节数不宜超过 50 章"


@pytest.mark.anyio
async def test_validate_input_step3_non_numeric_chapters_returns_error():
    """Error case: Step 3 章节范围非数字 → 返回 "章节范围必须是数字"。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {"volume_name": "第一卷", "chapter_start": "一", "chapter_end": "十"}

    result = await handler.validate_input(step, data)

    assert result == "章节范围必须是数字"


@pytest.mark.anyio
async def test_validate_input_step3_valid_data_returns_none():
    """Happy path: Step 3 所有必填项完整 → validate_input 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {
        "volume_name": "第一卷·初入江湖",
        "chapter_start": 1,
        "chapter_end": 20,
        "volume_theme": "主角成长",
    }

    result = await handler.validate_input(step, data)

    assert result is None


# ---------------------------------------------------------------------------
# Error case: execute_step 对未知 step_id 返回空 dict
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_unknown_step_id_returns_empty_dict():
    """execute_step 对未知 step_id（如 step_99）返回 {} 而不抛异常。"""
    handler = _handler()()
    step = StepState(step_id="step_99", status="running")

    result = await handler.execute_step(step, {})

    assert result == {}


# ---------------------------------------------------------------------------
# Edge case: validate_input 对其他步骤返回 None
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_validate_input_unknown_step_returns_none():
    """validate_input 对未知 step_id 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_99", status="waiting_input")

    result = await handler.validate_input(step, {})

    assert result is None
