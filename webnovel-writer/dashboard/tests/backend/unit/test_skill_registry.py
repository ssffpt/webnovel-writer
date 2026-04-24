"""Tests for SkillRegistry and EchoSkillHandler — TDD for Task 003."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_models import StepDefinition, StepState, SkillInstance
from dashboard.skill_runner import SkillHandler, SkillRunner


# ---------------------------------------------------------------------------
# SkillRegistry tests
# ---------------------------------------------------------------------------

def test_skill_registry_register_and_get():
    """注册后可以通过 get_handler 取回。"""
    from dashboard.skill_registry import SkillRegistry, EchoSkillHandler

    registry = SkillRegistry()
    registry.register("echo", EchoSkillHandler)

    handler = registry.get_handler("echo")
    assert handler is not None
    assert isinstance(handler, EchoSkillHandler)


def test_skill_registry_get_unknown_raises_keyerror():
    """get_handler 对不存在的 skill 抛出 KeyError。"""
    from dashboard.skill_registry import SkillRegistry

    registry = SkillRegistry()
    with pytest.raises(KeyError):
        registry.get_handler("nonexistent")


def test_skill_registry_list_skills():
    """list_skills 返回已注册的 skill 名称列表。"""
    from dashboard.skill_registry import SkillRegistry, EchoSkillHandler

    registry = SkillRegistry()
    assert registry.list_skills() == []

    registry.register("echo", EchoSkillHandler)
    assert set(registry.list_skills()) == {"echo"}


# ---------------------------------------------------------------------------
# EchoSkillHandler tests
# ---------------------------------------------------------------------------

def test_echo_skill_get_steps_returns_3_steps():
    """EchoSkillHandler.get_steps() 返回 3 个步骤定义。"""
    from dashboard.skill_registry import EchoSkillHandler

    handler = EchoSkillHandler()
    steps = handler.get_steps()

    assert len(steps) == 3
    assert [s.id for s in steps] == ["step_1", "step_2", "step_3"]
    assert [s.interaction for s in steps] == ["auto", "confirm", "auto"]


def test_echo_validate_input_rejects_empty_data():
    """validate_input 对空 data 返回错误信息。"""
    from dashboard.skill_registry import EchoSkillHandler

    handler = EchoSkillHandler()
    step = StepState(step_id="step_2", status="waiting_input")

    result = asyncio.get_event_loop().run_until_complete(
        handler.validate_input(step, {})
    )
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_echo_validate_input_accepts_nonempty_data():
    """validate_input 对非空 data 返回 None。"""
    from dashboard.skill_registry import EchoSkillHandler

    handler = EchoSkillHandler()
    step = StepState(step_id="step_2", status="waiting_input")

    result = asyncio.get_event_loop().run_until_complete(
        handler.validate_input(step, {"ok": True})
    )
    assert result is None


# ---------------------------------------------------------------------------
# Happy path: full echo skill flow
# ---------------------------------------------------------------------------

@pytest.fixture
def echo_instance():
    """Build a ready-to-run SkillInstance for the echo skill."""
    from dashboard.skill_registry import EchoSkillHandler

    handler = EchoSkillHandler()
    steps = handler.get_steps()

    instance = SkillInstance(
        id="echo-test-001",
        skill_name="echo",
        status="created",
        project_root="/tmp/echo-test",
        steps=steps,
        step_states=[],
        current_step_index=0,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        context={},
    )
    for step_def in steps:
        instance.step_states.append(
            StepState(step_id=step_def.id, status="pending")
        )
    if instance.step_states:
        instance.step_states[0].status = "waiting_input"
    return instance, handler


@pytest.mark.anyio
async def test_happy_path_echo_skill_runs_to_completion(echo_instance):
    """echo skill 走完全部 3 步后状态为 completed。"""
    instance, handler = echo_instance
    runner = SkillRunner(instance, handler)

    # step_1 (auto) runs, then stops at step_2 (confirm)
    await runner.start()
    assert instance.step_states[0].status == "done"
    assert instance.step_states[1].status == "waiting_input"
    assert instance.status == "running"

    # Submit input for step_2
    await runner.submit_input("step_2", {"ok": True})
    assert instance.step_states[1].status == "done"

    # step_3 (auto) should have run too
    assert instance.step_states[2].status == "done"
    assert instance.status == "completed"


@pytest.mark.anyio
async def test_echo_step_1_returns_prepare_complete(echo_instance):
    """step_1 执行后返回 {"message": "准备完成"}。"""
    instance, handler = echo_instance
    runner = SkillRunner(instance, handler)

    await runner.start()

    step1_state = instance.step_states[0]
    assert step1_state.status == "done"
    assert step1_state.output_data is not None
    assert step1_state.output_data.get("message") == "准备完成"


@pytest.mark.anyio
async def test_echo_step_3_returns_echo_context(echo_instance):
    """step_3 执行后 context 中包含 echo 结果。"""
    instance, handler = echo_instance
    runner = SkillRunner(instance, handler)

    await runner.start()
    await runner.submit_input("step_2", {"ok": True})

    step3_state = instance.step_states[2]
    assert step3_state.status == "done"
    assert step3_state.output_data is not None
    assert "message" in step3_state.output_data
    assert "echo" in step3_state.output_data
