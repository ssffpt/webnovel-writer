from __future__ import annotations

from pathlib import Path

from .test_phase1_contracts import create_app, make_project, request_json


def test_chat_response_includes_reason_and_scope_for_outline_page(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我继续",
            "context": {
                "page": "outline",
                "selectedPath": "大纲/卷一.md",
                "dirty": False,
            },
        },
    )

    assert status_code == 200
    assert payload["reply"]
    assert payload["suggested_actions"]
    assert payload["reason"]
    assert payload["scope"] == {
        "page": "outline",
        "selectedPath": "大纲/卷一.md",
    }


def test_same_message_routes_to_different_actions_by_page_context(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    outline_status, outline_payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我继续",
            "context": {
                "page": "outline",
                "selectedPath": "大纲/卷一.md",
                "dirty": False,
            },
        },
    )

    chapter_status, chapter_payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我继续",
            "context": {
                "page": "chapters",
                "selectedPath": "正文/第001章.md",
                "dirty": False,
            },
        },
    )

    assert outline_status == 200
    assert chapter_status == 200
    assert outline_payload["suggested_actions"][0]["type"] == "plan_outline"
    assert chapter_payload["suggested_actions"][0]["type"] == "write_chapter"
