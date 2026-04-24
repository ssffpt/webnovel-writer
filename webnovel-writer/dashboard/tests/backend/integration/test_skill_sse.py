"""Tests for Skill SSE event push — TDD for Task 005.

Verifies that Skill step transitions are emitted as SSE events through the
shared /api/events endpoint via a skill_q subscriber queue.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated_skill_sse_env(monkeypatch):
    """Patch _active_skills, _project_root, and _skill_subscribers.

    Since _skill_subscribers is an existing list, we replace the list's contents
    rather than replacing the reference so that all code that imports the module
    shares the same list object.
    """
    import dashboard.app as app_module

    isolated_active: dict = {}
    isolated_root = Path("/tmp/test-skill-sse")
    isolated_root.mkdir(exist_ok=True)

    monkeypatch.setattr(app_module, "_active_skills", isolated_active)
    monkeypatch.setattr(app_module, "_project_root", isolated_root)
    # Clear the real list and replace it with our isolated one
    app_module._skill_subscribers.clear()
    app_module._skill_subscribers.extend(isolated_subscribers := [])

    return {
        "active": isolated_active,
        "root": isolated_root,
        "monkeypatch": monkeypatch,
        "subscribers": isolated_subscribers,
    }


# ---------------------------------------------------------------------------
# Helper: drain a queue, collecting messages
# ---------------------------------------------------------------------------

async def drain_queue(q: asyncio.Queue, timeout: float = 3.0) -> list[dict]:
    """Drain all currently-available items from q within timeout."""
    items: list[dict] = []
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            break
        try:
            raw = await asyncio.wait_for(q.get(), timeout=remaining)
            items.append(json.loads(raw))
        except asyncio.TimeoutError:
            break
    return items


# ---------------------------------------------------------------------------
# Happy path: skill.step events emitted during auto-step execution
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_skill_step_events_emitted_during_start(isolated_skill_sse_env):
    """start_skill 后，auto step 的每步状态变化都会触发 skill.step 事件。"""
    import dashboard.app as app_module
    from dashboard.app import start_skill

    env = isolated_skill_sse_env
    # Subscribe before starting the skill so we don't miss events
    q = await app_module.subscribe_skill_events()
    env["subscribers"].append(q)

    result = await start_skill("echo", {"mode": "standard", "context": {}})

    # step_1 (auto) executes synchronously before start_skill returns,
    # so we may see step_1 running + done events.
    events = await drain_queue(q)

    # Should have at least one skill.step event
    step_events = [e for e in events if e.get("type") == "skill.step"]
    assert len(step_events) >= 1

    # step_1 auto step should have been marked done (no waiting_input event)
    # The flow should stop at step_2 (waiting_input)
    state_events = [e for e in events if e.get("type") in ("skill.step", "skill.completed", "skill.failed")]
    assert len(state_events) >= 1

    # skill_id must be present in all skill events
    for e in state_events:
        assert "skillId" in e
        assert e["skillId"] == result["id"]
        assert e["skillName"] == "echo"


@pytest.mark.anyio
async def test_skill_completed_event_emitted(isolated_skill_sse_env):
    """submit_skill_step 完成后，skill.completed 事件被推送。"""
    import dashboard.app as app_module
    from dashboard.app import start_skill, submit_skill_step

    env = isolated_skill_sse_env
    q = await app_module.subscribe_skill_events()
    env["subscribers"].append(q)

    result = await start_skill("echo", {"mode": "standard", "context": {}})
    skill_id = result["id"]

    # Drain any events from start
    await drain_queue(q, timeout=0.5)

    # Submit step_2 to complete the flow
    await submit_skill_step(skill_id, {"step_id": "step_2", "data": {"ok": True}})

    events = await drain_queue(q)

    completed = next((e for e in events if e.get("type") == "skill.completed"), None)
    assert completed is not None
    assert completed["skillId"] == skill_id
    assert completed["skillName"] == "echo"


# ---------------------------------------------------------------------------
# Happy path: skill.log events emitted
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_skill_log_event_emitted(isolated_skill_sse_env):
    """SkillService.push_skill_log() 推送 skill.log 事件。"""
    import dashboard.app as app_module

    env = isolated_skill_sse_env
    q = await app_module.subscribe_skill_events()
    env["subscribers"].append(q)

    await app_module.push_skill_log("test-skill-001", "test-message")

    events = await drain_queue(q, timeout=1.0)
    assert len(events) == 1
    assert events[0]["type"] == "skill.log"
    assert events[0]["skillId"] == "test-skill-001"
    assert events[0]["message"] == "test-message"


# ---------------------------------------------------------------------------
# Edge case 1: skill.failed event on step failure
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_skill_failed_event_emitted_on_error(isolated_skill_sse_env, monkeypatch):
    """execute_step 抛出异常时，skill.failed 事件被推送。"""
    import dashboard.app as app_module
    from dashboard.app import start_skill
    from dashboard.skill_handlers import EchoSkillHandler
    from dashboard.skill_models import SkillInstance, StepState
    from dashboard.skill_runner import SkillRunner

    env = isolated_skill_sse_env
    q = await app_module.subscribe_skill_events()
    env["subscribers"].append(q)

    # Replace EchoSkillHandler.execute_step with one that raises
    def failing_execute_step(self, step, context):
        raise RuntimeError("intentional failure")

    monkeypatch.setattr(EchoSkillHandler, "execute_step", failing_execute_step)

    result = await start_skill("echo", {"mode": "standard", "context": {}})
    skill_id = result["id"]

    events = await drain_queue(q)

    failed = next((e for e in events if e.get("type") == "skill.failed"), None)
    assert failed is not None
    assert failed["skillId"] == skill_id
    assert "intentional failure" in failed["error"]


# ---------------------------------------------------------------------------
# Edge case 2: multiple subscribers all receive events
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_multiple_subscribers_receive_events(isolated_skill_sse_env):
    """多个订阅者都能收到相同的 skill 事件。"""
    import dashboard.app as app_module
    from dashboard.app import start_skill, push_skill_log

    env = isolated_skill_sse_env
    q1 = await app_module.subscribe_skill_events()
    q2 = await app_module.subscribe_skill_events()
    env["subscribers"].append(q1)
    env["subscribers"].append(q2)

    await push_skill_log("multi-sub-001", "hello from multi-sub")

    events1 = await drain_queue(q1, timeout=1.0)
    events2 = await drain_queue(q2, timeout=1.0)

    assert len(events1) == 1
    assert len(events2) == 1
    assert events1[0] == events2[0]


# ---------------------------------------------------------------------------
# Error case: unsubscribe removes subscriber cleanly
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_unsubscribe_removes_subscriber(isolated_skill_sse_env):
    """unsubscribe_skill_events 正确移除订阅者，不再收到后续事件。"""
    import dashboard.app as app_module
    from dashboard.app import push_skill_log

    env = isolated_skill_sse_env
    q = await app_module.subscribe_skill_events()
    env["subscribers"].append(q)

    app_module.unsubscribe_skill_events(q)

    await push_skill_log("after-unsub", "should not arrive")

    events = await drain_queue(q, timeout=0.5)
    assert len(events) == 0
