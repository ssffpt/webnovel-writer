"""Tests for Skill API endpoints — TDD for Task 004.

Tests the skill API logic by calling route handler functions directly
(with module-level _active_skills patched to a test-local dict).
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# isolated_app fixture — patches module-level _active_skills and _project_root
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_skill_app(monkeypatch):
    """Patch _active_skills and _project_root so tests get isolated state."""
    from fastapi import HTTPException
    import dashboard.app as app_module

    # Isolated state
    isolated_active: dict = {}
    isolated_root = Path("/tmp/test-skill-api")
    isolated_root.mkdir(exist_ok=True)

    # Patch module-level globals used by the skill route functions
    monkeypatch.setattr(app_module, "_active_skills", isolated_active)
    monkeypatch.setattr(app_module, "_project_root", isolated_root)

    return {
        "active": isolated_active,
        "root": isolated_root,
        "monkeypatch": monkeypatch,
    }


@pytest.fixture
async def echo_runner_env(isolated_skill_app):
    """Pre-populate _active_skills with an EchoSkillRunner stopped at step_2."""
    from dashboard.skill_handlers import EchoSkillHandler
    from dashboard.skill_models import SkillInstance, StepState
    from dashboard.skill_runner import SkillRunner

    env = isolated_skill_app
    handler = EchoSkillHandler()
    steps = handler.get_steps(mode=None)

    instance = SkillInstance(
        id="echo-test-001",
        skill_name="echo",
        status="created",
        project_root=str(env["root"]),
        steps=steps,
        step_states=[],
        current_step_index=0,
        context={},
    )
    for step_def in steps:
        instance.step_states.append(StepState(step_id=step_def.id, status="pending"))

    runner = SkillRunner(instance, handler)
    env["active"]["echo-test-001"] = runner

    # Run start(): auto step_1 executes, stops at step_2 waiting_input
    await runner.start()

    return env


# ---------------------------------------------------------------------------
# Happy path: POST /api/skill/echo/start
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_start_skill_returns_instance_dict(isolated_skill_app):
    """start_skill 返回包含 id/skill_name/status 的 dict。"""
    from dashboard.app import start_skill

    env = isolated_skill_app
    result = await start_skill("echo", {"mode": "standard", "context": {}})

    assert "id" in result
    assert result["skill_name"] == "echo"
    assert result["status"] in ("running", "created")


@pytest.mark.anyio
async def test_start_skill_returns_3_steps(isolated_skill_app):
    """start_skill 响应的 steps 列表长度为 3。"""
    from dashboard.app import start_skill

    env = isolated_skill_app
    result = await start_skill("echo", {"mode": "standard", "context": {}})

    assert "steps" in result
    assert len(result["steps"]) == 3


@pytest.mark.anyio
async def test_start_skill_registers_runner(isolated_skill_app):
    """start_skill 后 runner 被注册到 _active_skills。"""
    from dashboard.app import start_skill

    env = isolated_skill_app
    result = await start_skill("echo", {"mode": "standard", "context": {}})

    skill_id = result["id"]
    assert skill_id in env["active"]


# ---------------------------------------------------------------------------
# Happy path: GET /api/skill/{skill_id}/status
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_status_returns_instance_dict(echo_runner_env):
    """get_skill_status 返回 SkillInstance.to_dict()。"""
    from dashboard.app import get_skill_status

    result = await get_skill_status("echo-test-001")

    assert result["id"] == "echo-test-001"
    assert "steps" in result
    assert "step_states" in result


# ---------------------------------------------------------------------------
# Happy path: POST /api/skill/{id}/step
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_step_submits_input_and_completes(echo_runner_env):
    """submit_skill_step 提交 step_2 后流程完成。"""
    from dashboard.app import submit_skill_step

    result = await submit_skill_step(
        "echo-test-001",
        {"step_id": "step_2", "data": {"ok": True}},
    )

    assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Happy path: POST /api/skill/{id}/cancel
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_cancel_marks_instance_cancelled(echo_runner_env):
    """cancel_skill 返回 cancelled 状态。"""
    from dashboard.app import cancel_skill

    result = await cancel_skill("echo-test-001")

    assert result["status"] == "cancelled"


# ---------------------------------------------------------------------------
# Happy path: GET /api/skill/active
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_active_returns_instances_list(echo_runner_env):
    """list_active_skills 返回包含 instances 列表的 dict。"""
    from dashboard.app import list_active_skills

    result = await list_active_skills()

    assert "instances" in result
    assert isinstance(result["instances"], list)
    assert len(result["instances"]) >= 1


# ---------------------------------------------------------------------------
# Edge case 1: POST /api/skill/unknown/start → 400
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_start_unknown_skill_returns_400(isolated_skill_app, monkeypatch):
    """start_skill 对未注册的 skill 抛出 HTTPException 400。"""
    from fastapi import HTTPException
    from dashboard import skill_registry as sr_module

    env = isolated_skill_app
    mock = MagicMock()
    mock.get_handler.side_effect = KeyError("no such skill")
    monkeypatch.setattr(sr_module, "default_registry", mock)

    from dashboard.app import start_skill

    with pytest.raises(HTTPException) as exc_info:
        await start_skill("unknown", {"mode": "standard", "context": {}})
    assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# Edge case 2: POST /api/skill/{id}/step 提交任意 form 数据
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_step_accepts_arbitrary_form_data(echo_runner_env):
    """submit_skill_step 提交任意 data dict 后流程继续。"""
    from dashboard.app import submit_skill_step

    result = await submit_skill_step(
        "echo-test-001",
        {"step_id": "step_2", "data": {"user_name": "test", "count": 99}},
    )

    assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Error case: GET /api/skill/nonexistent-id/status → 404
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_get_status_unknown_id_returns_404(isolated_skill_app):
    """get_skill_status 对不存在的 skill_id 抛出 HTTPException 404。"""
    from fastapi import HTTPException
    from dashboard.app import get_skill_status

    with pytest.raises(HTTPException) as exc_info:
        await get_skill_status("nonexistent-skill-id")
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_step_unknown_id_returns_404(isolated_skill_app):
    """submit_skill_step 对不存在的 skill_id 抛出 HTTPException 404。"""
    from fastapi import HTTPException
    from dashboard.app import submit_skill_step

    with pytest.raises(HTTPException) as exc_info:
        await submit_skill_step("nonexistent-skill-id", {"step_id": "step_1", "data": {}})
    assert exc_info.value.status_code == 404


@pytest.mark.anyio
async def test_cancel_unknown_id_returns_404(isolated_skill_app):
    """cancel_skill 对不存在的 skill_id 抛出 HTTPException 404。"""
    from fastapi import HTTPException
    from dashboard.app import cancel_skill

    with pytest.raises(HTTPException) as exc_info:
        await cancel_skill("nonexistent-skill-id")
    assert exc_info.value.status_code == 404
