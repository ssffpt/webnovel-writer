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


def test_settings_page_routes_to_inspect_setting_on_continue(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我继续",
            "context": {
                "page": "settings",
                "selectedPath": "设定集/主角.md",
                "dirty": False,
            },
        },
    )

    assert status_code == 200
    assert payload["suggested_actions"][0]["type"] == "inspect_setting"
    assert payload["reason"]


def test_dirty_context_suggests_save_first_and_returns_no_actions(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我规划第二卷",
            "context": {
                "page": "outline",
                "selectedPath": "大纲/卷一.md",
                "dirty": True,
            },
        },
    )

    assert status_code == 200
    assert payload["suggested_actions"] == []
    assert "未保存" in payload["reply"]
    assert payload["reason"]


def test_selected_path_passed_through_to_action_params(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "写下一章",
            "context": {
                "page": "chapters",
                "selectedPath": "正文/第001章.md",
                "dirty": False,
            },
        },
    )

    assert status_code == 200
    assert payload["suggested_actions"][0]["params"]["path"] == "正文/第001章.md"


def test_chat_without_context_still_returns_reason_and_scope(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))

    status_code, payload = request_json(
        app,
        "POST",
        "/api/chat",
        {"message": "帮我写章节"},
    )

    assert status_code == 200
    assert payload["reply"]
    assert payload["reason"]
    assert "scope" in payload


def test_ambiguous_keyword_routes_by_page_context(tmp_path: Path) -> None:
    """When keywords match multiple action types, page context breaks the tie."""
    app = create_app(make_project(tmp_path))

    # "检查" on chapters page -> review_chapter
    ch_status, ch_payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "帮我检查",
            "context": {"page": "chapters", "dirty": False},
        },
    )
    assert ch_status == 200
    assert ch_payload["suggested_actions"][0]["type"] == "review_chapter"

    # "检查" on settings page -> inspect_setting (via "帮我继续" fallback)
    # "设定" keyword on settings page -> inspect_setting
    st_status, st_payload = request_json(
        app,
        "POST",
        "/api/chat",
        {
            "message": "检查设定冲突",
            "context": {"page": "settings", "dirty": False},
        },
    )
    assert st_status == 200
    assert st_payload["suggested_actions"][0]["type"] == "inspect_setting"
