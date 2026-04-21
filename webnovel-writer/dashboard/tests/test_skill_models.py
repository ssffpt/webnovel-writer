"""Tests for skill_models.py — TDD for Task 001."""
from __future__ import annotations

import pytest
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_models import (
    StepDefinition,
    StepState,
    SkillInstance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_skill_instance(
    skill_name: str = "init",
    status: str = "created",
    mode: str | None = None,
    project_root: str = "/tmp/test-project",
    steps: list[StepDefinition] | None = None,
) -> SkillInstance:
    if steps is None:
        steps = [
            StepDefinition(id="step_1", name="步骤一", interaction="auto"),
            StepDefinition(id="step_2", name="步骤二", interaction="form"),
            StepDefinition(id="step_3", name="步骤三", interaction="confirm"),
        ]
    return SkillInstance(
        id="test-uuid-001",
        skill_name=skill_name,
        status=status,
        mode=mode,
        project_root=project_root,
        steps=steps,
        step_states=[],
        current_step_index=0,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        context={},
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_skill_instance_roundtrip():
    """创建 SkillInstance → 序列化 → 反序列化 → 字段一致."""
    original = make_skill_instance(
        skill_name="write",
        status="running",
        mode="standard",
        project_root="/path/to/project",
    )
    original.step_states = [
        StepState(step_id="step_1", status="done"),
        StepState(step_id="step_2", status="running", progress=0.5),
    ]
    original.context["key"] = "value"

    serialized = original.to_dict()
    restored = SkillInstance.from_dict(serialized)

    assert restored.id == original.id
    assert restored.skill_name == original.skill_name
    assert restored.status == original.status
    assert restored.mode == original.mode
    assert restored.project_root == original.project_root
    assert restored.current_step_index == original.current_step_index
    assert restored.context == original.context
    assert len(restored.steps) == len(original.steps)
    assert len(restored.step_states) == len(original.step_states)
    assert restored.step_states[1].status == "running"
    assert restored.step_states[1].progress == 0.5


def test_step_definition_serialization():
    """StepDefinition 序列化/反序列化."""
    step = StepDefinition(
        id="step_2",
        name="采集用户输入",
        interaction="form",
        skippable=True,
    )
    data = step.to_dict()
    restored = StepDefinition.from_dict(data)

    assert restored.id == step.id
    assert restored.name == step.name
    assert restored.interaction == step.interaction
    assert restored.skippable == step.skippable


def test_step_state_serialization():
    """StepState 序列化/反序列化."""
    state = StepState(
        step_id="step_1",
        status="done",
        started_at="2026-01-01T00:00:00",
        completed_at="2026-01-01T00:01:00",
        input_data={"book_title": "测试书"},
        output_data={"book_id": "abc123"},
        error=None,
        progress=1.0,
    )
    data = state.to_dict()
    restored = StepState.from_dict(data)

    assert restored.step_id == state.step_id
    assert restored.status == state.status
    assert restored.input_data == state.input_data
    assert restored.output_data == state.output_data
    assert restored.progress == 1.0


# ---------------------------------------------------------------------------
# Edge case 1: advance() 到最后一步后返回 False
# ---------------------------------------------------------------------------

def test_advance_returns_true_when_more_steps():
    """advance() 在有后续步骤时返回 True."""
    instance = make_skill_instance()
    instance.step_states = [
        StepState(step_id="step_1", status="done"),
        StepState(step_id="step_2", status="pending"),
        StepState(step_id="step_3", status="pending"),
    ]
    instance.current_step_index = 0

    assert instance.advance() is True
    assert instance.current_step_index == 1


def test_advance_returns_false_when_at_last_step():
    """advance() 到最后一步后返回 False."""
    instance = make_skill_instance()
    instance.step_states = [
        StepState(step_id="step_1", status="done"),
        StepState(step_id="step_2", status="done"),
        StepState(step_id="step_3", status="done"),
    ]
    instance.current_step_index = 2

    assert instance.advance() is False
    assert instance.current_step_index == 2  # unchanged


def test_advance_updates_step_state_status():
    """advance() 同时更新被推进步骤的状态."""
    instance = make_skill_instance()
    instance.step_states = [
        StepState(step_id="step_1", status="done"),
        StepState(step_id="step_2", status="pending"),
        StepState(step_id="step_3", status="pending"),
    ]
    instance.current_step_index = 0
    instance.advance()
    # step 2 is now waiting_input
    assert instance.step_states[1].status == "waiting_input"


# ---------------------------------------------------------------------------
# Edge case 2: is_terminal() 在各状态下的返回值
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status,expected", [
    ("created", False),
    ("running", False),
    ("completed", True),
    ("failed", True),
    ("cancelled", True),
])
def test_is_terminal(status: str, expected: bool):
    """is_terminal() 对应各 status 的返回值."""
    instance = make_skill_instance(status=status)
    assert instance.is_terminal() is expected


# ---------------------------------------------------------------------------
# Error case: from_dict() 传入缺失字段时抛出明确异常
# ---------------------------------------------------------------------------

def test_from_dict_raises_on_missing_required_field():
    """from_dict() 传入缺失字段时抛出 KeyError."""
    data = {"id": "uuid-1"}  # 缺少 skill_name 等字段
    with pytest.raises(KeyError) as exc_info:
        SkillInstance.from_dict(data)
    assert "skill_name" in str(exc_info.value)


def test_from_dict_raises_on_completely_invalid_data():
    """from_dict() 传入非 dict 时抛出 TypeError."""
    with pytest.raises(TypeError):
        SkillInstance.from_dict("not a dict")


def test_step_definition_from_dict_raises_on_missing_id():
    """StepDefinition.from_dict() 缺少 id 时抛出."""
    data = {"name": "test", "interaction": "auto"}
    with pytest.raises(KeyError):
        StepDefinition.from_dict(data)


def test_step_state_from_dict_raises_on_missing_step_id():
    """StepState.from_dict() 缺少 step_id 时抛出."""
    data = {"status": "pending"}
    with pytest.raises(KeyError):
        StepState.from_dict(data)


# ---------------------------------------------------------------------------
# current_step()
# ---------------------------------------------------------------------------

def test_current_step_returns_current_step_state():
    """current_step() 返回当前步骤状态."""
    instance = make_skill_instance()
    instance.step_states = [
        StepState(step_id="step_1", status="done"),
        StepState(step_id="step_2", status="waiting_input"),
        StepState(step_id="step_3", status="pending"),
    ]
    instance.current_step_index = 1
    current = instance.current_step()
    assert current is not None
    assert current.step_id == "step_2"
    assert current.status == "waiting_input"


def test_current_step_returns_none_when_no_step_states():
    """current_step() 在无 step_states 时返回 None."""
    instance = make_skill_instance()
    instance.step_states = []
    assert instance.current_step() is None


# ---------------------------------------------------------------------------
# is_terminal() edge: status not in terminal set
# ---------------------------------------------------------------------------

def test_is_terminal_false_for_unknown_status():
    """is_terminal() 对未知 status 也返回 False."""
    instance = make_skill_instance(status="unknown_status")
    assert instance.is_terminal() is False


# ---------------------------------------------------------------------------
# advance() edge: no step_states
# ---------------------------------------------------------------------------

def test_advance_no_step_states():
    """advance() 在无 step_states 时返回 False."""
    instance = make_skill_instance()
    instance.step_states = []
    assert instance.advance() is False


def test_advance_empty_steps_list():
    """advance() 在 steps 为空时返回 False."""
    instance = make_skill_instance(steps=[])
    instance.step_states = []
    assert instance.advance() is False
