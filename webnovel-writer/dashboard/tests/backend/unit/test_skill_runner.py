"""Tests for skill_runner.py — TDD for Task 002."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_models import (
    StepDefinition,
    StepState,
    SkillInstance,
)
from dashboard.skill_runner import SkillHandler, SkillRunner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_3auto_steps() -> list[StepDefinition]:
    """3 步全 auto 的步骤定义."""
    return [
        StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        StepDefinition(id="step_2", name="步骤二", interaction="auto"),
        StepDefinition(id="step_3", name="步骤三", interaction="auto"),
    ]


def make_form_skill() -> list[StepDefinition]:
    """中间有 form 步骤的 Skill."""
    return [
        StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        StepDefinition(id="step_2", name="采集输入", interaction="form"),
        StepDefinition(id="step_3", name="步骤三", interaction="auto"),
    ]


def make_instance(
    steps: list[StepDefinition] | None = None,
    status: str = "created",
    skill_name: str = "init",
    project_root: str = "/tmp/test-project",
) -> SkillInstance:
    steps = steps or make_3auto_steps()
    instance = SkillInstance(
        id="test-runner-001",
        skill_name=skill_name,
        status=status,
        project_root=project_root,
        steps=steps,
        step_states=[],
        current_step_index=0,
        created_at="2026-01-01T00:00:00",
        updated_at="2026-01-01T00:00:00",
        context={},
    )
    # Initialise step_states from definitions
    for step_def in steps:
        instance.step_states.append(
            StepState(
                step_id=step_def.id,
                status="pending",
            )
        )
    # First step starts as waiting_input
    if instance.step_states:
        instance.step_states[0].status = "waiting_input"
    return instance


# ---------------------------------------------------------------------------
# Mock handlers
# ---------------------------------------------------------------------------

class RecordingHandler(SkillHandler):
    """Records calls for assertions; fully async to match the interface."""

    def __init__(self, steps: list[StepDefinition]):
        self._steps = steps
        self.execute_calls: list[tuple[StepState, dict]] = []
        self.validate_calls: list[tuple[StepState, dict]] = []
        self._validate_error: str | None = None

    def set_validate_error(self, msg: str) -> None:
        self._validate_error = msg

    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return self._steps

    async def execute_step(self, step: StepState, context: dict) -> dict:
        self.execute_calls.append((step, context))
        # Return unique output so callers can distinguish steps
        return {"executed": step.step_id}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        self.validate_calls.append((step, data))
        return self._validate_error


# ---------------------------------------------------------------------------
# Happy path: 3 步全 auto → start() → 自动走完 → status == "completed"
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_happy_path_3auto_runs_to_completion():
    """全 auto Skill 启动后自动执行完全部步骤并标记 completed."""
    instance = make_instance(steps=make_3auto_steps())
    handler = RecordingHandler(make_3auto_steps())

    runner = SkillRunner(instance, handler)
    await runner.start()

    # All steps executed
    assert len(handler.execute_calls) == 3

    # Instance is completed
    assert instance.status == "completed"

    # All step states are "done"
    for state in instance.step_states:
        assert state.status == "done", f"step {state.step_id} status is {state.status}"


@pytest.mark.anyio
async def test_happy_path_all_steps_have_timestamps():
    """Completed steps have started_at and completed_at timestamps."""
    instance = make_instance(steps=make_3auto_steps())
    handler = RecordingHandler(make_3auto_steps())

    runner = SkillRunner(instance, handler)
    await runner.start()

    for state in instance.step_states:
        assert state.started_at is not None
        assert state.completed_at is not None
        assert state.started_at <= state.completed_at


@pytest.mark.anyio
async def test_happy_path_context_accumulates_step_outputs():
    """Each step's output_data is accumulated into context."""
    instance = make_instance(steps=make_3auto_steps())
    handler = RecordingHandler(make_3auto_steps())

    runner = SkillRunner(instance, handler)
    await runner.start()

    for state in instance.step_states:
        assert state.output_data is not None
        assert "executed" in state.output_data


# ---------------------------------------------------------------------------
# Edge case 1: 中间有 form 步骤 → start() 停在 waiting_input
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_form_step_stops_at_waiting_input():
    """form 步骤停在 waiting_input，submit_input() 后继续执行."""
    instance = make_instance(steps=make_form_skill())
    handler = RecordingHandler(make_form_skill())

    runner = SkillRunner(instance, handler)
    await runner.start()

    # Only step 1 (auto) executed
    assert len(handler.execute_calls) == 1
    assert handler.execute_calls[0][0].step_id == "step_1"

    # step 2 is waiting_input
    assert instance.step_states[1].status == "waiting_input"
    # instance still running (not terminal)
    assert instance.status == "running"

    # Now submit input for step 2
    await runner.submit_input("step_2", {"user_input": "hello"})

    # Step 2 should have executed and step 3 should be done (auto)
    assert len(handler.execute_calls) == 3
    assert len(handler.validate_calls) == 1
    assert handler.validate_calls[0][1] == {"user_input": "hello"}

    assert instance.status == "completed"


@pytest.mark.anyio
async def test_form_step_validate_input_rejection():
    """validate_input() 返回错误时 submit_input() 不执行步骤."""
    instance = make_instance(steps=make_form_skill())
    handler = RecordingHandler(make_form_skill())
    handler.set_validate_error("Field 'user_input' is required")

    runner = SkillRunner(instance, handler)
    await runner.start()

    # Try to submit invalid input
    await runner.submit_input("step_2", {})

    # Still only 1 execute call (no new step executed)
    assert len(handler.execute_calls) == 1
    # step 2 still waiting_input
    assert instance.step_states[1].status == "waiting_input"


@pytest.mark.anyio
async def test_confirm_step_behaves_like_form():
    """confirm 步骤与 form 步骤行为一致：等待输入后继续."""
    steps = [
        StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        StepDefinition(id="step_2", name="确认", interaction="confirm"),
        StepDefinition(id="step_3", name="步骤三", interaction="auto"),
    ]
    instance = make_instance(steps=steps)
    handler = RecordingHandler(steps)

    runner = SkillRunner(instance, handler)
    await runner.start()

    assert instance.step_states[1].status == "waiting_input"
    await runner.submit_input("step_2", {"confirmed": True})

    assert instance.status == "completed"
    assert len(handler.execute_calls) == 3


# ---------------------------------------------------------------------------
# Edge case 2: resume() 从 JSON 恢复后继续执行剩余步骤
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resume_continues_from_interrupted_state():
    """从 JSON 恢复后，继续执行剩余 auto 步骤."""
    steps = [
        StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        StepDefinition(id="step_2", name="步骤二", interaction="auto"),
        StepDefinition(id="step_3", name="步骤三", interaction="auto"),
    ]

    # Build an instance where step 1 is done and step 2 is the current step
    data = {
        "id": "resume-test-001",
        "skill_name": "init",
        "status": "running",
        "mode": None,
        "project_root": "/tmp/test-project",
        "steps": [s.to_dict() for s in steps],
        "step_states": [
            {
                "step_id": "step_1",
                "status": "done",
                "started_at": "2026-01-01T00:00:00",
                "completed_at": "2026-01-01T00:00:05",
                "input_data": None,
                "output_data": {"executed": "step_1"},
                "error": None,
                "progress": 1.0,
            },
            {
                "step_id": "step_2",
                "status": "waiting_input",
                "started_at": None,
                "completed_at": None,
                "input_data": None,
                "output_data": None,
                "error": None,
                "progress": 0.0,
            },
            {
                "step_id": "step_3",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "input_data": None,
                "output_data": None,
                "error": None,
                "progress": 0.0,
            },
        ],
        "current_step_index": 1,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:05",
        "context": {},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "resume-test-001.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        handler = RecordingHandler(steps)
        runner = await SkillRunner.resume(path, handler)

        # current_step_index should be restored
        assert runner.instance.current_step_index == 1

        # Start should auto-execute remaining steps
        await runner.start()

        # step_2 and step_3 should have executed
        executed_ids = [call[0].step_id for call in handler.execute_calls]
        assert "step_2" in executed_ids
        assert "step_3" in executed_ids

        assert runner.instance.status == "completed"


@pytest.mark.anyio
async def test_resume_from_waiting_input():
    """从 waiting_input 状态恢复，等待用户输入."""
    steps = [
        StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        StepDefinition(id="step_2", name="采集输入", interaction="form"),
        StepDefinition(id="step_3", name="步骤三", interaction="auto"),
    ]

    data = {
        "id": "resume-form-001",
        "skill_name": "init",
        "status": "running",
        "mode": None,
        "project_root": "/tmp/test-project",
        "steps": [s.to_dict() for s in steps],
        "step_states": [
            {
                "step_id": "step_1",
                "status": "done",
                "started_at": "2026-01-01T00:00:00",
                "completed_at": "2026-01-01T00:00:05",
                "input_data": None,
                "output_data": {"executed": "step_1"},
                "error": None,
                "progress": 1.0,
            },
            {
                "step_id": "step_2",
                "status": "waiting_input",
                "started_at": None,
                "completed_at": None,
                "input_data": None,
                "output_data": None,
                "error": None,
                "progress": 0.0,
            },
            {
                "step_id": "step_3",
                "status": "pending",
                "started_at": None,
                "completed_at": None,
                "input_data": None,
                "output_data": None,
                "error": None,
                "progress": 0.0,
            },
        ],
        "current_step_index": 1,
        "created_at": "2026-01-01T00:00:00",
        "updated_at": "2026-01-01T00:00:05",
        "context": {},
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "resume-form-001.json"
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

        handler = RecordingHandler(steps)
        runner = await SkillRunner.resume(path, handler)

        # Should be waiting on step_2
        assert runner.instance.current_step().step_id == "step_2"
        assert runner.instance.current_step().status == "waiting_input"

        # submit_input should continue
        await runner.submit_input("step_2", {"answer": 42})
        assert runner.instance.status == "completed"


# ---------------------------------------------------------------------------
# Error case: execute_step() 抛异常 → 步骤 status == "failed",
#            instance status == "failed"
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_execute_step_exception_marks_step_and_instance_failed():
    """execute_step() 抛异常时，步骤标记为 failed，instance 也标记为 failed."""

    class FailingHandler(SkillHandler):
        def get_steps(self, mode=None):
            return [
                StepDefinition(id="step_1", name="步骤一", interaction="auto"),
                StepDefinition(id="step_2", name="步骤二", interaction="auto"),
            ]

        async def execute_step(self, step, context):
            if step.step_id == "step_2":
                raise RuntimeError("something went wrong")
            return {"executed": step.step_id}

        async def validate_input(self, step, data):
            return None

    steps = [
        StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        StepDefinition(id="step_2", name="步骤二", interaction="auto"),
    ]
    instance = make_instance(steps=steps)
    handler = FailingHandler()

    runner = SkillRunner(instance, handler)
    await runner.start()

    # step_1 succeeded
    assert instance.step_states[0].status == "done"
    # step_2 failed
    assert instance.step_states[1].status == "failed"
    assert instance.step_states[1].error is not None
    assert "something went wrong" in instance.step_states[1].error
    # instance is failed
    assert instance.status == "failed"


@pytest.mark.anyio
async def test_error_on_first_auto_step_fails_instance():
    """第一步就失败时，instance 直接标记为 failed."""
    steps = [StepDefinition(id="step_1", name="步骤一", interaction="auto")]

    class AlwaysFails(SkillHandler):
        def get_steps(self, mode=None):
            return steps

        async def execute_step(self, step, context):
            raise ValueError("boom")

        async def validate_input(self, step, data):
            return None

    instance = make_instance(steps=steps)
    handler = AlwaysFails()

    runner = SkillRunner(instance, handler)
    await runner.start()

    assert instance.status == "failed"
    assert instance.step_states[0].status == "failed"


# ---------------------------------------------------------------------------
# cancel() 行为
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cancel_marks_instance_cancelled():
    """cancel() 将 instance status 设为 cancelled."""
    instance = make_instance(steps=make_3auto_steps())
    handler = RecordingHandler(make_3auto_steps())

    runner = SkillRunner(instance, handler)
    await runner.start()

    # Cancel during execution (before all done)
    # We need to interrupt — easiest way is to use form step
    form_steps = make_form_skill()
    instance2 = make_instance(steps=form_steps)
    handler2 = RecordingHandler(form_steps)
    runner2 = SkillRunner(instance2, handler2)
    await runner2.start()

    # Now cancel
    await runner2.cancel()
    assert instance2.status == "cancelled"


@pytest.mark.anyio
async def test_cancel_does_not_advance_after_waiting_input():
    """cancel() 后不会再处理 submit_input."""
    form_steps = make_form_skill()
    instance = make_instance(steps=form_steps)
    handler = RecordingHandler(form_steps)
    runner = SkillRunner(instance, handler)
    await runner.start()

    await runner.cancel()
    await runner.submit_input("step_2", {"user_input": "x"})

    # submit_input should be no-op after cancel
    assert len(handler.execute_calls) == 1
    assert instance.status == "cancelled"


# ---------------------------------------------------------------------------
# get_state() 返回完整状态
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_state_returns_full_instance_state():
    """get_state() 返回 SkillInstance.to_dict()."""
    instance = make_instance(steps=make_3auto_steps())
    handler = RecordingHandler(make_3auto_steps())
    runner = SkillRunner(instance, handler)

    state = runner.get_state()
    assert isinstance(state, dict)
    assert state["id"] == "test-runner-001"
    assert state["skill_name"] == "init"
    assert state["status"] == "created"


# ---------------------------------------------------------------------------
# on_step_change callback
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_on_step_change_callback_fires_on_status_change():
    """每次步骤状态变化时 on_step_change 回调被调用."""
    calls: list[tuple[SkillInstance, StepState]] = []

    def callback(inst: SkillInstance, step: StepState):
        calls.append((inst, step))

    instance = make_instance(steps=make_3auto_steps(), project_root="/tmp/test-project")
    handler = RecordingHandler(make_3auto_steps())
    runner = SkillRunner(instance, handler, on_step_change=callback)

    await runner.start()

    # Should have been called at least 3 times (once per step status change)
    # plus initial waiting_input and done transitions
    assert len(calls) >= 3


# ---------------------------------------------------------------------------
# Persistence: 状态变化后写入 JSON
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_persistence_writes_json_on_step_change():
    """步骤状态变化后将 instance 写入 JSON 文件."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = tmpdir

        # Create instance with this project_root
        instance = make_instance(
            steps=make_3auto_steps(),
            project_root=project_root,
        )
        handler = RecordingHandler(make_3auto_steps())
        runner = SkillRunner(instance, handler)

        await runner.start()

        # Check that the file was written
        instances_dir = Path(project_root) / ".webnovel" / "workflow" / "instances"
        assert instances_dir.exists()
        files = list(instances_dir.glob("*.json"))
        assert len(files) == 1

        # File should contain completed status
        data = json.loads(files[0].read_text(encoding="utf-8"))
        assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# Workflow manager dual-write (best-effort)
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_workflow_manager_dual_write_on_start():
    """start() 时双写 workflow_state.json（best-effort，不阻断主流程）."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = tmpdir

        # workflow_manager.py requires .webnovel/state.json to exist.
        webnovel_dir = Path(project_root) / ".webnovel"
        webnovel_dir.mkdir(parents=True, exist_ok=True)
        (webnovel_dir / "state.json").write_text(
            json.dumps({"project": "test", "chapters": []}), encoding="utf-8"
        )

        steps = [
            StepDefinition(id="step_1", name="步骤一", interaction="auto"),
        ]
        instance = make_instance(steps=steps, project_root=project_root)
        handler = RecordingHandler(steps)
        runner = SkillRunner(instance, handler)

        await runner.start()

        # Should have written workflow_state.json
        state_file = Path(project_root) / ".webnovel" / "workflow_state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text(encoding="utf-8"))
        assert state["current_task"] is None  # cleared by complete-task
        assert state["last_stable_state"] is not None
        assert state["last_stable_state"]["command"] == "webnovel-init"


# ---------------------------------------------------------------------------
# submit_input 错误 step_id
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_submit_input_wrong_step_id_raises():
    """submit_input() 传入非当前步骤 id 时抛出 ValueError."""
    form_steps = make_form_skill()
    instance = make_instance(steps=form_steps)
    handler = RecordingHandler(form_steps)
    runner = SkillRunner(instance, handler)
    await runner.start()

    with pytest.raises(ValueError) as exc_info:
        await runner.submit_input("step_3", {})  # wrong step
    assert "step_3" in str(exc_info.value)


# ---------------------------------------------------------------------------
# resume() 类方法: 文件不存在时抛出 FileNotFoundError
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_resume_raises_on_missing_file():
    """resume() 文件不存在时抛出 FileNotFoundError."""
    handler = RecordingHandler(make_3auto_steps())

    with pytest.raises(FileNotFoundError):
        await SkillRunner.resume(Path("/nonexistent/path.json"), handler)


# ---------------------------------------------------------------------------
# start() on already-running instance: no-op or raises
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_start_on_running_instance_raises():
    """已在 running 状态的实例再次 start() 抛出 RuntimeError."""
    form_steps = make_form_skill()
    instance = make_instance(steps=form_steps)
    handler = RecordingHandler(form_steps)
    runner = SkillRunner(instance, handler)
    await runner.start()

    with pytest.raises(RuntimeError) as exc_info:
        await runner.start()
    assert "twice" in str(exc_info.value).lower() or "terminal" in str(exc_info.value).lower()
