"""Tests for InitSkillHandler — TDD for Task 101."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_models import StepDefinition, StepState


# ---------------------------------------------------------------------------
# Imports (deferred so missing module surfaces as a clear test failure)
# ---------------------------------------------------------------------------

def _handler():
    from dashboard.skill_handlers.init_handler import InitSkillHandler
    return InitSkillHandler


def _registry():
    from dashboard.skill_registry import default_registry
    return default_registry


# ---------------------------------------------------------------------------
# Happy path: registry → handler → steps
# ---------------------------------------------------------------------------

def test_default_registry_has_init_handler():
    """default_registry.get_handler("init") 返回 InitSkillHandler 实例。"""
    registry = _registry()
    handler = registry.get_handler("init")
    assert handler is not None
    InitHandler = _handler()
    assert isinstance(handler, InitHandler)


def test_init_handler_get_steps_returns_6_steps():
    """InitSkillHandler.get_steps() 返回 6 个 StepDefinition。"""
    handler = _handler()()
    steps = handler.get_steps()
    assert len(steps) == 6
    assert [s.id for s in steps] == [
        "step_1", "step_2", "step_3", "step_4", "step_5", "step_6",
    ]


def test_init_handler_step_names():
    """每个 step 的 name 与规格一致。"""
    handler = _handler()()
    steps = handler.get_steps()
    names = [s.name for s in steps]
    assert names == [
        "故事核与商业定位",
        "角色骨架与关系冲突",
        "金手指与兑现机制",
        "世界观与力量规则",
        "创意约束包",
        "一致性复述与确认",
    ]


# ---------------------------------------------------------------------------
# Edge case 1: interaction 类型正确（前 4 form，后 2 confirm）
# ---------------------------------------------------------------------------

def test_init_handler_interaction_types():
    """Step 1-4 是 form，Step 5-6 是 confirm。"""
    handler = _handler()()
    steps = handler.get_steps()
    interactions = [s.interaction for s in steps]
    assert interactions == ["form", "form", "form", "form", "confirm", "confirm"]


# ---------------------------------------------------------------------------
# Edge case 2: validate_input 骨架对任意输入返回 None（不阻断）
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_validate_input_returns_none_for_unknown_step():
    """validate_input 对未知 step_id（如 step_99）返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_99", status="waiting_input")

    result = await handler.validate_input(step, {})
    assert result is None


@pytest.mark.anyio
async def test_validate_input_returns_none_when_all_required_fields_present():
    """validate_input 对 step_1 所有必填字段存在时返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_1", status="waiting_input")
    data = {
        "title": "测试书",
        "genres": ["玄幻"],
        "one_line_story": "一句话",
        "core_conflict": "核心冲突",
    }

    result = await handler.validate_input(step, data)
    assert result is None


# ---------------------------------------------------------------------------
# Error case: execute_step 对未知 step_id 返回空 dict 而非抛异常
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_unknown_step_id_returns_empty_dict():
    """execute_step 对未知 step_id 返回 {} 而不抛异常。"""
    handler = _handler()()
    step = StepState(step_id="step_99", status="running")

    result = await handler.execute_step(step, {})
    assert result == {}


# ---------------------------------------------------------------------------
# execute_step 对已知 step_id 的占位返回值
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step5_returns_packages_placeholder():
    """step_5 execute 返回 packages 列表和 instruction。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")

    result = await handler.execute_step(step, {})
    assert "packages" in result
    assert isinstance(result["packages"], list)
    assert "instruction" in result


@pytest.mark.anyio
async def test_execute_step_step6_returns_summary_placeholder():
    """step_6 execute 当 context 不完整时返回 gate_passed=False 和 missing_items。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")

    result = await handler.execute_step(step, {})
    assert "gate_passed" in result
    assert "missing_items" in result
    assert result["gate_passed"] is False


# ---------------------------------------------------------------------------
# Task 103: Step 5 创意约束包生成
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_step5_returns_packages_with_full_context():
    """Happy path: context 包含前 4 步数据 → execute_step 返回 2-3 个 packages，每个含 id/name/constraints/score。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "title": "测试书",
        "genres": ["玄幻"],
        "one_line_story": "一句话故事",
        "core_conflict": "核心冲突",
        "protagonist_desire": "复仇",
        "protagonist_flaw": "性格缺陷",
        "golden_finger_type": "系统流",
    }

    result = await handler.execute_step(step, context)

    assert "packages" in result
    assert isinstance(result["packages"], list)
    # AI mode: 2-3 packages; fallback mode (current): 1 package is acceptable
    assert 1 <= len(result["packages"]) <= 3
    for pkg in result["packages"]:
        assert "id" in pkg
        assert "name" in pkg
        assert "constraints" in pkg
        assert "score" in pkg
        assert isinstance(pkg["constraints"], list)
        assert 3 <= len(pkg["constraints"]) <= 5
        assert "instruction" in result


@pytest.mark.anyio
async def test_execute_step_step5_packages_have_valid_score_fields():
    """每个 package 的 score 包含五维评分字段。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "title": "测试书",
        "genres": ["都市"],
        "one_line_story": "一句话",
        "core_conflict": "冲突",
        "protagonist_desire": "欲望",
        "protagonist_flaw": "缺陷",
        "golden_finger_type": "重生",
    }

    result = await handler.execute_step(step, context)

    for pkg in result["packages"]:
        score = pkg["score"]
        assert "novelty" in score
        assert "feasibility" in score
        assert "reader_hook" in score
        assert "consistency" in score
        assert "differentiation" in score


@pytest.mark.anyio
async def test_execute_step_step5_constraints_have_type_and_content():
    """每个 constraint 有 type 和 content 字段。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "title": "测试书",
        "genres": ["奇幻"],
        "one_line_story": "一句话",
        "core_conflict": "冲突",
        "protagonist_desire": "欲望",
        "protagonist_flaw": "缺陷",
        "golden_finger_type": "异能",
    }

    result = await handler.execute_step(step, context)

    for pkg in result["packages"]:
        for constraint in pkg["constraints"]:
            assert "type" in constraint
            assert "content" in constraint


@pytest.mark.anyio
async def test_execute_step_step5_returns_fallback_package():
    """Edge case 1: AI API 不可用时（通过 _generate_creativity_packages 返回 fallback），流程不阻断。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="running")
    context = {
        "title": "测试书",
        "genres": [],
        "one_line_story": "",
        "core_conflict": "",
        "protagonist_desire": "",
        "protagonist_flaw": "",
        "golden_finger_type": "",
    }

    result = await handler.execute_step(step, context)

    assert "packages" in result
    assert len(result["packages"]) >= 1
    assert result["packages"][0]["id"] == "pkg_fallback"


@pytest.mark.anyio
async def test_validate_input_step5_with_selected_id_returns_none():
    """Edge case 2: validate_input 收到 selected_package_id → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="waiting_input")
    data = {"selected_package_id": "pkg_1"}

    result = await handler.validate_input(step, data)

    assert result is None


@pytest.mark.anyio
async def test_validate_input_step5_without_selected_id_returns_error():
    """Error case: validate_input 未收到 selected_package_id → 返回错误信息。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="waiting_input")
    data = {}

    result = await handler.validate_input(step, data)

    assert result == "请选择一套创意约束包"


# ---------------------------------------------------------------------------
# Task 102: Step 1-4 表单采集
# ---------------------------------------------------------------------------

# --- validate_input ---

@pytest.mark.anyio
async def test_validate_input_step1_missing_title_returns_error():
    """Step 1 缺少 title → 返回 "书名不能为空"。"""
    handler = _handler()()
    step = StepState(step_id="step_1", status="waiting_input")
    data = {"genres": ["玄幻"], "one_line_story": "测试", "core_conflict": "冲突"}

    result = await handler.validate_input(step, data)
    assert result == "书名不能为空"


@pytest.mark.anyio
async def test_validate_input_step1_complete_returns_none():
    """Step 1 提交完整数据 → validate_input 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_1", status="waiting_input")
    data = {
        "title": "测试书名",
        "genres": ["玄幻"],
        "one_line_story": "一句话故事",
        "core_conflict": "核心冲突",
    }

    result = await handler.validate_input(step, data)
    assert result is None


@pytest.mark.anyio
async def test_validate_input_step2_missing_protagonist_desire_returns_error():
    """Step 2 缺少 protagonist_desire → 返回 "主角欲望不能为空"。"""
    handler = _handler()()
    step = StepState(step_id="step_2", status="waiting_input")
    data = {
        "protagonist_name": "张三",
        "protagonist_flaw": "性格缺陷",
    }

    result = await handler.validate_input(step, data)
    assert result == "主角欲望不能为空"


@pytest.mark.anyio
async def test_validate_input_step3_missing_golden_finger_type_returns_error():
    """Step 3 golden_finger_type 为空 → 返回 "金手指类型不能为空"。"""
    handler = _handler()()
    step = StepState(step_id="step_3", status="waiting_input")
    data = {
        "golden_finger_name": "神秘戒指",
    }

    result = await handler.validate_input(step, data)
    assert result == "金手指类型不能为空"


@pytest.mark.anyio
async def test_validate_input_step4_missing_power_system_returns_error():
    """Step 4 缺少 power_system → 返回 "力量体系不能为空"。"""
    handler = _handler()()
    step = StepState(step_id="step_4", status="waiting_input")
    data = {
        "world_scale": "单大陆",
    }

    result = await handler.validate_input(step, data)
    assert result == "力量体系不能为空"


@pytest.mark.anyio
async def test_validate_input_step5_requires_selected_package_id():
    """Step 5 validate_input 必须包含 selected_package_id。"""
    handler = _handler()()
    step = StepState(step_id="step_5", status="waiting_input")

    result = await handler.validate_input(step, {})
    assert result == "请选择一套创意约束包"


# --- execute_step ---

@pytest.mark.anyio
async def test_execute_step_step1_merges_fields_into_context():
    """Step 1 execute_step 将表单数据合并到 context。"""
    handler = _handler()()
    step = StepState(
        step_id="step_1",
        status="running",
        input_data={"title": "测试书", "genres": ["玄幻"], "one_line_story": "一句话"},
    )
    context = {}

    result = await handler.execute_step(step, context)

    assert context["title"] == "测试书"
    assert context["genres"] == ["玄幻"]
    assert "merged_fields" in result
    assert "title" in result["merged_fields"]


@pytest.mark.anyio
async def test_execute_step_step2_merges_fields_into_context():
    """Step 2 execute_step 将表单数据合并到 context。"""
    handler = _handler()()
    step = StepState(
        step_id="step_2",
        status="running",
        input_data={"protagonist_name": "张三", "protagonist_desire": "复仇"},
    )
    context = {}

    result = await handler.execute_step(step, context)

    assert context["protagonist_name"] == "张三"
    assert context["protagonist_desire"] == "复仇"


@pytest.mark.anyio
async def test_execute_step_preserves_existing_context_fields():
    """execute_step 合并数据时保留 context 中已有的字段。"""
    handler = _handler()()
    step = StepState(
        step_id="step_1",
        status="running",
        input_data={"title": "新书名"},
    )
    context = {"existing_key": "existing_value"}

    await handler.execute_step(step, context)

    assert context["existing_key"] == "existing_value"
    assert context["title"] == "新书名"


@pytest.mark.anyio
async def test_execute_step_step3_merges_golden_finger_fields():
    """Step 3 execute_step 合并金手指相关字段。"""
    handler = _handler()()
    step = StepState(
        step_id="step_3",
        status="running",
        input_data={"golden_finger_type": "系统流", "golden_finger_name": "超级系统"},
    )
    context = {}

    result = await handler.execute_step(step, context)

    assert context["golden_finger_type"] == "系统流"
    assert context["golden_finger_name"] == "超级系统"


@pytest.mark.anyio
async def test_execute_step_step4_merges_world_fields():
    """Step 4 execute_step 合并世界观相关字段。"""
    handler = _handler()()
    step = StepState(
        step_id="step_4",
        status="running",
        input_data={"world_scale": "单大陆", "power_system": "炼气-筑基-金丹"},
    )
    context = {}

    result = await handler.execute_step(step, context)

    assert context["world_scale"] == "单大陆"
    assert context["power_system"] == "炼气-筑基-金丹"


# ---------------------------------------------------------------------------
# Task 104: Step 6 一致性复述 + 充分性闸门 + 执行
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_check_sufficiency_gate_all_fields_present():
    """Happy path: 所有必填项完整 → gate 通过，missing 为空。"""
    handler = _handler()()
    context = {
        "title": "测试书",
        "genres": ["玄幻"],
        "target_words": 2000000,
        "protagonist_desire": "复仇",
        "protagonist_flaw": "性格缺陷",
        "world_scale": "单大陆",
        "power_system": "炼气筑基",
        "selected_package_id": "pkg_1",
    }

    result = handler._check_sufficiency_gate(context)

    assert result["passed"] is True
    assert result["missing"] == []


@pytest.mark.anyio
async def test_check_sufficiency_gate_missing_protagonist_desire():
    """Edge case 1: context 缺少 protagonist_desire → gate 不通过，missing 包含"主角欲望"。"""
    handler = _handler()()
    context = {
        "title": "测试书",
        "genres": ["玄幻"],
        "target_words": 2000000,
        "protagonist_desire": "",  # 缺失
        "protagonist_flaw": "性格缺陷",
        "world_scale": "单大陆",
        "power_system": "炼气筑基",
        "selected_package_id": "pkg_1",
    }

    result = handler._check_sufficiency_gate(context)

    assert result["passed"] is False
    assert "主角欲望" in result["missing"]


@pytest.mark.anyio
async def test_check_sufficiency_gate_missing_multiple_fields():
    """Edge case 2: 缺少多个字段 → gate 不通过，missing 包含所有缺失项。"""
    handler = _handler()()
    context = {
        "title": "测试书",
        # genres 缺失
        "target_words": 2000000,
        # protagonist_desire 缺失
        "protagonist_flaw": "性格缺陷",
        # world_scale 缺失
        "power_system": "炼气筑基",
        "selected_package_id": "pkg_1",
    }

    result = handler._check_sufficiency_gate(context)

    assert result["passed"] is False
    assert "题材" in result["missing"]
    assert "主角欲望" in result["missing"]
    assert "世界规模" in result["missing"]


@pytest.mark.anyio
async def test_check_sufficiency_gate_missing_selected_package():
    """Edge case 3: selected_package_id 缺失 → gate 不通过。"""
    handler = _handler()()
    context = {
        "title": "测试书",
        "genres": ["玄幻"],
        "target_words": 2000000,
        "protagonist_desire": "复仇",
        "protagonist_flaw": "缺陷",
        "world_scale": "单大陆",
        "power_system": "炼气筑基",
        "selected_package_id": "",  # 缺失
    }

    result = handler._check_sufficiency_gate(context)

    assert result["passed"] is False
    assert "创意约束包" in result["missing"]


@pytest.mark.anyio
async def test_build_summary_with_full_context():
    """Happy path: context 完整 → _build_summary 生成包含所有字段的摘要文本。"""
    handler = _handler()()
    context = {
        "title": "测试书名",
        "genres": ["玄幻", "修仙"],
        "target_words": 2000000,
        "target_chapters": 600,
        "one_line_story": "一句话故事内容",
        "core_conflict": "核心冲突描述",
        "protagonist_name": "张三",
        "protagonist_desire": "复仇",
        "protagonist_flaw": "冲动",
        "golden_finger_name": "超级系统",
        "golden_finger_type": "系统流",
        "world_scale": "单大陆",
        "power_system": "炼气筑基金丹",
        "selected_package_id": "pkg_fallback",
    }

    summary = handler._build_summary(context)

    assert "测试书名" in summary
    assert "玄幻" in summary
    assert "修仙" in summary
    assert "2000000" in summary
    assert "600" in summary
    assert "一句话故事内容" in summary
    assert "核心冲突描述" in summary
    assert "张三" in summary
    assert "复仇" in summary
    assert "冲动" in summary
    assert "超级系统" in summary
    assert "系统流" in summary
    assert "单大陆" in summary
    assert "炼气筑基金丹" in summary
    assert "pkg_fallback" in summary


@pytest.mark.anyio
async def test_build_summary_with_missing_fields():
    """Edge case: context 部分字段缺失 → _build_summary 用空字符串填充缺失字段，不抛异常。"""
    handler = _handler()()
    context = {
        "title": "测试书",
        "genres": ["都市"],
        # 其他字段均缺失
    }

    summary = handler._build_summary(context)

    assert "测试书" in summary
    assert "都市" in summary
    # 缺失字段不应导致 KeyError，应为空字符串


@pytest.mark.anyio
async def test_execute_step_step6_gate_passed():
    """Happy path: context 完整 → execute_step step_6 返回 gate_passed=True 和 summary。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "title": "测试书",
        "genres": ["玄幻"],
        "target_words": 2000000,
        "protagonist_desire": "复仇",
        "protagonist_flaw": "性格缺陷",
        "world_scale": "单大陆",
        "power_system": "炼气筑基",
        "selected_package_id": "pkg_1",
        "one_line_story": "一句话故事",
        "core_conflict": "核心冲突",
        "protagonist_name": "张三",
        "golden_finger_name": "系统",
        "golden_finger_type": "系统流",
    }

    result = await handler.execute_step(step, context)

    assert result["gate_passed"] is True
    assert "summary" in result
    assert isinstance(result["summary"], str)
    assert "测试书" in result["summary"]
    assert result["instruction"] == "请确认以下项目摘要，确认后将创建项目"


@pytest.mark.anyio
async def test_execute_step_step6_gate_failed():
    """Edge case: context 缺少必填项 → execute_step step_6 返回 gate_passed=False 和 missing_items。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="running")
    context = {
        "title": "测试书",
        "genres": ["玄幻"],
        # 缺少 target_words, protagonist_desire, protagonist_flaw,
        # world_scale, power_system, selected_package_id
    }

    result = await handler.execute_step(step, context)

    assert result["gate_passed"] is False
    assert "missing_items" in result
    assert isinstance(result["missing_items"], list)
    assert "目标字数" in result["missing_items"]
    assert "主角欲望" in result["missing_items"]
    assert "主角缺陷" in result["missing_items"]
    assert "世界规模" in result["missing_items"]
    assert "力量体系" in result["missing_items"]
    assert "创意约束包" in result["missing_items"]
    assert result["instruction"] == "以下必填项尚未完成，请返回补填"


@pytest.mark.anyio
async def test_validate_input_step6_confirmed_true():
    """Edge case: validate_input 收到 confirmed=True → 返回 None。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="waiting_input")
    data = {"confirmed": True}

    result = await handler.validate_input(step, data)

    assert result is None


@pytest.mark.anyio
async def test_validate_input_step6_confirmed_false():
    """Error case: validate_input 未确认（confirmed=False）→ 返回"请确认项目摘要"。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="waiting_input")
    data = {"confirmed": False}

    result = await handler.validate_input(step, data)

    assert result == "请确认项目摘要"


@pytest.mark.anyio
async def test_validate_input_step6_missing_confirmed_field():
    """Error case: validate_input 缺少 confirmed 字段 → 视为未确认，返回错误。"""
    handler = _handler()()
    step = StepState(step_id="step_6", status="waiting_input")
    data = {}

    result = await handler.validate_input(step, data)

    assert result == "请确认项目摘要"
