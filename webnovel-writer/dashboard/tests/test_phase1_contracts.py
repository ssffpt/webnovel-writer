from __future__ import annotations

import json
import sys
from asyncio import run
from pathlib import Path
from urllib.parse import urlencode

REPO_WEBNOVEL_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_WEBNOVEL_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_WEBNOVEL_ROOT))

from dashboard.app import create_app  # noqa: E402


def make_project(tmp_path: Path) -> Path:
    project_root = tmp_path / "demo-project"
    webnovel_dir = project_root / ".webnovel"
    webnovel_dir.mkdir(parents=True)

    (webnovel_dir / "state.json").write_text(
        json.dumps(
            {
                "project_info": {
                    "title": "测试小说",
                    "genre": "玄幻",
                    "target_words": 500000,
                    "target_chapters": 200,
                },
                "progress": {
                    "current_chapter": 12,
                    "current_volume": 2,
                    "total_words": 88000,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    for folder in ("正文", "大纲", "设定集"):
        (project_root / folder).mkdir()

    (project_root / "正文" / "第001章.md").write_text("旧正文", encoding="utf-8")
    (project_root / "大纲" / "卷一.md").write_text("旧大纲", encoding="utf-8")
    (project_root / "设定集" / "主角.md").write_text("旧设定", encoding="utf-8")
    return project_root


def request_json(app, method: str, path: str, payload: dict | None = None, params: dict | None = None):
    body = b""
    raw_path = path
    query_string = b""
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if params:
        query_string = urlencode(params, doseq=True).encode("utf-8")

    async def _call():
        messages: list[dict] = []
        request_complete = False

        async def receive():
            nonlocal request_complete
            if request_complete:
                return {"type": "http.disconnect"}
            request_complete = True
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode("utf-8"),
            "query_string": query_string,
            "headers": [
                (b"host", b"testserver"),
                (b"content-type", b"application/json"),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }

        await app(scope, receive, send)

        start = next(message for message in messages if message["type"] == "http.response.start")
        body_chunks = [
            message.get("body", b"")
            for message in messages
            if message["type"] == "http.response.body"
        ]
        response_body = b"".join(body_chunks).decode("utf-8")
        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError:
            payload = {"_raw": response_body}
        return start["status"], payload

    return run(_call())


def test_workbench_summary_exposes_overview_and_workspace_roots(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status_code, payload = request_json(app, "GET", "/api/workbench/summary")

    assert status_code == 200
    assert payload["pages"] == ["overview", "chapters", "outline", "settings"]
    assert payload["project"]["title"] == "测试小说"
    assert payload["workspace_roots"] == ["正文", "大纲", "设定集"]
    assert payload["workspaces"]["chapters"]["root"] == "正文"
    assert payload["workspaces"]["outline"]["root"] == "大纲"
    assert payload["workspaces"]["settings"]["root"] == "设定集"



def test_current_task_returns_idle_placeholder(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status_code, payload = request_json(app, "GET", "/api/tasks/current")

    assert status_code == 200
    assert payload == {
        "status": "idle",
        "task": None,
        "step": None,
        "updatedAt": None,
    }



def test_chat_returns_outline_action_for_outline_request(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我规划第二卷",
            "context": {"page": "outline", "selectedPath": "大纲/卷一.md"},
        },
    )

    assert status_code == 200
    assert payload["reply"]
    assert payload["suggested_actions"] == [
        {
            "type": "plan_outline",
            "label": "生成当前卷纲",
            "params": {"path": "大纲/卷一.md"},
        }
    ]



def test_save_file_writes_allowed_workspace_file(tmp_path: Path) -> None:
    project_root = make_project(tmp_path)
    app = create_app(project_root)
    status_code, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": "正文/第001章.md", "content": "新正文"},
    )

    assert status_code == 200
    assert payload["path"] == "正文/第001章.md"
    assert payload["size"] == len("新正文".encode("utf-8"))
    saved = project_root / "正文" / "第001章.md"
    assert saved.read_text(encoding="utf-8") == "新正文"



def test_save_file_rejects_path_outside_workspace_roots(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status_code, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": ".webnovel/state.json", "content": "{}"},
    )

    assert status_code == 403
    assert "正文/大纲/设定集" in payload["detail"]


def test_workbench_summary_degrades_when_workspace_directories_are_missing(tmp_path: Path) -> None:
    project_root = make_project(tmp_path)
    (project_root / "设定集" / "主角.md").unlink()
    (project_root / "设定集").rmdir()
    app = create_app(project_root)

    status_code, payload = request_json(app, "GET", "/api/workbench/summary")

    assert status_code == 200
    assert payload["workspaces"]["settings"] == {
        "root": "设定集",
        "exists": False,
        "file_count": 0,
    }


def test_save_file_can_create_new_file_inside_allowed_workspace(tmp_path: Path) -> None:
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    status_code, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": "大纲/卷二/第010章.md", "content": "新增章纲"},
    )

    assert status_code == 200
    assert payload["path"] == "大纲/卷二/第010章.md"
    assert (project_root / "大纲" / "卷二" / "第010章.md").read_text(encoding="utf-8") == "新增章纲"


def test_save_file_rejects_non_string_payload_fields(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": ["正文/第001章.md"], "content": {"text": "bad"}},
    )

    assert status_code == 400
    assert payload["detail"] == "path 和 content 必须为字符串"


def test_chat_rejects_non_string_message(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {"message": {"text": "bad"}, "context": {"page": "outline"}},
    )

    assert status_code == 400
    assert payload["detail"] == "message 必须为字符串"


def test_chat_rejects_non_object_context(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {"message": "帮我规划第二卷", "context": "outline"},
    )

    assert status_code == 400
    assert payload["detail"] == "context 必须为对象"


def test_unknown_api_route_returns_json_404_instead_of_spa_html(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(app, "GET", "/api/does-not-exist")

    assert status_code == 404
    assert payload["detail"] == "API 路由不存在"
