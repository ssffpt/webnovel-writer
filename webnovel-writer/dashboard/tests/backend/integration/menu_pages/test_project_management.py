"""集成测试：项目管理 API（remove / rename / cleanup）。

覆盖：
- POST /api/project/remove   从注册表移除项目
- POST /api/project/rename   重命名项目
- POST /api/project/cleanup  清理无效记录
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_WEBNOVEL_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_WEBNOVEL_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_WEBNOVEL_ROOT))

from dashboard.app import create_app  # noqa: E402
from dashboard.tests.backend.integration.test_phase1_contracts import (  # noqa: E402
    make_project,
    request_json,
)
from dashboard.project_service import _read_workspaces  # noqa: E402


# ---------------------------------------------------------------------------
# POST /api/project/remove
# ---------------------------------------------------------------------------

def test_remove_project_from_registry(tmp_path: Path) -> None:
    """移除项目后，注册表中不再包含该项目。"""
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    # 先切换项目确保它被注册
    status, _ = request_json(app, "POST", "/api/project/switch", {"path": str(project_root)})
    assert status == 200

    # 验证注册表中有该项目
    registry = _read_workspaces()
    assert str(project_root) in registry["workspaces"]

    # 调用 remove（不从磁盘删除）
    status, payload = request_json(
        app, "POST", "/api/project/remove", {"path": str(project_root), "delete_dir": False}
    )
    assert status == 200
    assert payload["success"] is True

    # 验证注册表中已移除
    registry = _read_workspaces()
    assert str(project_root) not in registry["workspaces"]
    # 目录应仍然存在
    assert project_root.exists()


def test_remove_project_with_delete_dir(tmp_path: Path) -> None:
    """remove 时 delete_dir=true 会同时删除目录。"""
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    request_json(app, "POST", "/api/project/switch", {"path": str(project_root)})

    status, payload = request_json(
        app, "POST", "/api/project/remove", {"path": str(project_root), "delete_dir": True}
    )
    assert status == 200
    assert payload["success"] is True

    # 目录应被删除
    assert not project_root.exists()


def test_remove_nonexistent_project_returns_400(tmp_path: Path) -> None:
    """移除不在注册表中的项目返回 400。"""
    app = create_app(make_project(tmp_path))

    status, payload = request_json(
        app, "POST", "/api/project/remove", {"path": "/nonexistent/path"}
    )
    assert status == 400


# ---------------------------------------------------------------------------
# POST /api/project/rename
# ---------------------------------------------------------------------------

def test_rename_project_updates_state_json(tmp_path: Path) -> None:
    """重命名后 state.json 中的 title 被更新。"""
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    status, payload = request_json(
        app,
        "POST",
        "/api/project/rename",
        {"path": str(project_root), "title": "新书名"},
    )
    assert status == 200
    assert payload["success"] is True

    # 验证 state.json
    state_path = project_root / ".webnovel" / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["project_info"]["title"] == "新书名"


def test_rename_project_rejects_empty_title(tmp_path: Path) -> None:
    """空标题返回 400。"""
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    status, payload = request_json(
        app, "POST", "/api/project/rename", {"path": str(project_root), "title": "  "}
    )
    assert status == 400


def test_rename_invalid_project_returns_400(tmp_path: Path) -> None:
    """重命名无效路径返回 400。"""
    app = create_app(make_project(tmp_path))

    status, payload = request_json(
        app, "POST", "/api/project/rename", {"path": "/nonexistent", "title": "新名字"}
    )
    assert status == 400


# ---------------------------------------------------------------------------
# POST /api/project/cleanup
# ---------------------------------------------------------------------------

def test_cleanup_removes_nonexistent_entries(tmp_path: Path) -> None:
    """清理后注册表中不再包含已删除的目录。"""
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    # 注册当前项目
    request_json(app, "POST", "/api/project/switch", {"path": str(project_root)})

    # 手动在注册表中添加一个不存在的路径（模拟僵尸记录）
    from dashboard.project_service import _read_workspaces, _write_workspaces
    registry = _read_workspaces()
    fake_path = "/tmp/fake-nonexistent-project-12345"
    registry["workspaces"][fake_path] = {
        "workspace_root": fake_path,
        "current_project_root": fake_path,
        "updated_at": "2026-01-01T00:00:00",
    }
    _write_workspaces(registry)

    # 验证注册表中有僵尸记录
    registry = _read_workspaces()
    assert fake_path in registry["workspaces"]
    assert str(project_root) in registry["workspaces"]

    # 调用 cleanup
    status, payload = request_json(app, "POST", "/api/project/cleanup", {})
    assert status == 200
    assert payload["success"] is True
    assert fake_path in payload["removed"]

    # 验证僵尸记录被清理，真实项目保留
    registry = _read_workspaces()
    assert fake_path not in registry["workspaces"]
    assert str(project_root) in registry["workspaces"]


def test_cleanup_resets_current_if_current_removed(tmp_path: Path) -> None:
    """如果当前项目被清理，last_used_project_root 应被重置。"""
    project_root = make_project(tmp_path)
    app = create_app(project_root)

    request_json(app, "POST", "/api/project/switch", {"path": str(project_root)})

    # 删除目录但保留注册表记录
    import shutil
    shutil.rmtree(project_root, ignore_errors=True)

    status, payload = request_json(app, "POST", "/api/project/cleanup", {})
    assert status == 200
    assert str(project_root) in payload["removed"]

    registry = _read_workspaces()
    assert registry.get("last_used_project_root") != str(project_root)
