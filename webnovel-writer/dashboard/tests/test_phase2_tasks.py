from __future__ import annotations

import time
from pathlib import Path

from .test_phase1_contracts import create_app, make_project, request_json


def test_create_task_returns_pending_task_with_id(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/tasks",
        {
            "action": {
                "type": "plan_outline",
                "label": "生成当前卷纲",
                "params": {"path": "大纲/卷一.md"},
            },
            "context": {
                "page": "outline",
                "selectedPath": "大纲/卷一.md",
            },
        },
    )

    assert status_code in (200, 202)
    assert payload["id"]
    assert payload["status"] == "pending"
    assert payload["action"]["type"] == "plan_outline"
    assert payload["createdAt"]
    assert payload["updatedAt"]
    assert payload["logs"] == []
    assert payload["result"] is None
    assert payload["error"] is None


def test_post_tasks_creates_task_and_get_task_returns_same_task(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    create_status, created = request_json(
        app,
        "POST",
        "/api/tasks",
        {
            "action": {
                "type": "write_chapter",
                "label": "生成当前章节",
                "params": {"path": "正文/第001章.md"},
            },
            "context": {
                "page": "chapters",
                "selectedPath": "正文/第001章.md",
            },
        },
    )

    get_status, fetched = request_json(app, "GET", f"/api/tasks/{created['id']}")

    assert create_status in (200, 202)
    assert get_status == 200
    assert fetched["id"] == created["id"]
    assert fetched["status"] in ("pending", "running")
    assert fetched["action"] == created["action"]
    assert fetched["createdAt"] == created["createdAt"]
    assert fetched["updatedAt"] >= created["updatedAt"]


def test_background_task_transitions_to_completed_with_logs_and_result(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    create_status, created = request_json(
        app,
        "POST",
        "/api/tasks",
        {
            "action": {
                "type": "inspect_setting",
                "label": "检查当前设定冲突",
                "params": {"path": "设定集/主角.md"},
            },
            "context": {
                "page": "settings",
                "selectedPath": "设定集/主角.md",
            },
        },
    )

    assert create_status in (200, 202)

    deadline = time.time() + 2.0
    last_payload = None
    while time.time() < deadline:
        get_status, fetched = request_json(app, "GET", f"/api/tasks/{created['id']}")
        assert get_status == 200
        last_payload = fetched
        if fetched["status"] == "completed":
            break
        time.sleep(0.05)

    assert last_payload is not None
    assert last_payload["status"] == "completed"
    assert last_payload["logs"]
    assert last_payload["result"] is not None
    assert last_payload["error"] is None


def test_background_task_transitions_to_failed_with_error_and_logs(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    create_status, created = request_json(
        app,
        "POST",
        "/api/tasks",
        {
            "action": {
                "type": "force_fail",
                "label": "强制失败任务",
                "params": {"path": "设定集/主角.md"},
            },
            "context": {
                "page": "settings",
                "selectedPath": "设定集/主角.md",
            },
        },
    )

    assert create_status in (200, 202)

    deadline = time.time() + 2.0
    last_payload = None
    while time.time() < deadline:
        get_status, fetched = request_json(app, "GET", f"/api/tasks/{created['id']}")
        assert get_status == 200
        last_payload = fetched
        if fetched["status"] == "failed":
            break
        time.sleep(0.05)

    assert last_payload is not None
    assert last_payload["status"] == "failed"
    assert last_payload["logs"]
    assert last_payload["result"] is None
    assert last_payload["error"]
