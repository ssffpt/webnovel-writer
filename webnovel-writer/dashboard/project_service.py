"""项目创建、列表、切换服务层。

使用 subprocess 调用 init_project.py（避免 import 冲突），
直接读取 workspaces.json 注册表（避免 project_locator.py 的依赖问题）。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _projects_root() -> Path:
    """项目存储根目录，默认 ~/webnovel-projects/，可通过环境变量覆盖。"""
    env = os.environ.get("WEBNOVEL_PROJECTS_ROOT")
    if env:
        return Path(env).expanduser()
    return Path.home() / "webnovel-projects"


def _generate_project_dir(title: str) -> Path:
    """生成项目目录路径，冲突时追加数字后缀。"""
    base = _projects_root()
    base.mkdir(parents=True, exist_ok=True)
    candidate = base / title
    if not candidate.exists():
        return candidate
    n = 2
    while (base / f"{title}-{n}").exists():
        n += 1
    return base / f"{title}-{n}"


def _workspaces_json_path() -> Path:
    """workspaces.json 的路径，与 project_locator.py 一致。"""
    claude_home = os.environ.get(
        "CLAUDE_HOME",
        os.environ.get("WEBNOVEL_CLAUDE_HOME", str(Path.home() / ".claude")),
    )
    return Path(claude_home) / "webnovel-writer" / "workspaces.json"


def _read_workspaces() -> dict:
    """读取 workspaces.json 注册表。"""
    path = _workspaces_json_path()
    if not path.is_file():
        return {"schema_version": 1, "workspaces": {}, "last_used_project_root": None, "updated_at": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"schema_version": 1, "workspaces": {}, "last_used_project_root": None, "updated_at": None}


def _write_workspaces(registry: dict) -> None:
    """写入 workspaces.json 注册表。"""
    path = _workspaces_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def _register_project(project_root: Path) -> None:
    """将项目注册到 workspaces.json。"""
    registry = _read_workspaces()
    key = str(project_root)
    registry["workspaces"][key] = {
        "workspace_root": str(project_root),
        "current_project_root": str(project_root),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    registry["last_used_project_root"] = str(project_root)
    _write_workspaces(registry)


def create_project(payload: dict, package_root: Path) -> dict:
    """创建新项目。

    1. 生成 project_dir
    2. subprocess 调用 init_project.py
    3. 注册到 workspaces.json
    4. 返回结果
    """
    title = payload.get("title", "")
    genre = payload.get("genre", "")
    project_dir = _generate_project_dir(title)

    # 构建 CLI 命令
    script_path = package_root / "scripts" / "init_project.py"
    cmd = [sys.executable, str(script_path), str(project_dir), title, genre]

    # 可选参数
    if payload.get("protagonist_name"):
        cmd += ["--protagonist-name", str(payload["protagonist_name"])]
    if payload.get("target_words"):
        cmd += ["--target-words", str(int(payload["target_words"]))]
    if payload.get("target_chapters"):
        cmd += ["--target-chapters", str(int(payload["target_chapters"]))]
    if payload.get("golden_finger_name"):
        cmd += ["--golden-finger-name", str(payload["golden_finger_name"])]
    if payload.get("golden_finger_type"):
        cmd += ["--golden-finger-type", str(payload["golden_finger_type"])]
    if payload.get("core_selling_points"):
        cmd += ["--core-selling-points", str(payload["core_selling_points"])]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return {
            "success": False,
            "error": result.stderr or result.stdout or "项目创建失败",
            "project_root": str(project_dir),
            "state": None,
        }

    # 注册
    _register_project(project_dir)

    # 读取生成的 state.json
    state_path = project_dir / ".webnovel" / "state.json"
    state = None
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "success": True,
        "project_root": str(project_dir),
        "state": state,
    }


def list_projects() -> dict:
    """列出已注册的项目，过滤掉已不存在的目录。"""
    registry = _read_workspaces()
    current = registry.get("last_used_project_root")
    projects: list[dict[str, Any]] = []

    for _key, ws in registry.get("workspaces", {}).items():
        project_root = Path(ws.get("current_project_root", ws.get("workspace_root", "")))
        # 跳过已不存在的目录（清理僵尸记录）
        if not project_root.exists():
            continue
        state_path = project_root / ".webnovel" / "state.json"
        info: dict[str, Any] = {
            "name": "未知项目",
            "path": str(project_root),
            "genre": None,
            "current_chapter": 0,
            "last_updated": ws.get("updated_at"),
        }
        if state_path.is_file():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                pi = state.get("project_info", {})
                prog = state.get("progress", {})
                info["name"] = pi.get("title") or "未命名"
                info["genre"] = pi.get("genre")
                info["current_chapter"] = prog.get("current_chapter", 0)
            except (json.JSONDecodeError, OSError):
                pass
        projects.append(info)

    return {"projects": projects, "current": current}


def switch_project(target_path: str) -> dict:
    """切换到目标项目。校验路径有效性，更新注册表。"""
    target = Path(target_path).resolve()
    state_path = target / ".webnovel" / "state.json"
    if not state_path.is_file():
        return {"success": False, "error": f"目标路径不是有效的网文项目: {target_path}"}

    # 更新注册表
    _register_project(target)

    return {"success": True, "project_root": str(target)}


def remove_project_from_registry(project_path: str) -> dict:
    """从注册表中移除项目（不删除实际目录）。"""
    registry = _read_workspaces()
    key = str(Path(project_path).resolve())
    if key not in registry.get("workspaces", {}):
        return {"success": False, "error": "项目不在注册表中"}
    del registry["workspaces"][key]
    # 如果删除的是当前项目，重置 current
    if registry.get("last_used_project_root") == key:
        registry["last_used_project_root"] = None
    _write_workspaces(registry)
    return {"success": True}


def rename_project(project_path: str, new_title: str) -> dict:
    """重命名项目：更新 state.json 中的 title。"""
    target = Path(project_path).resolve()
    state_path = target / ".webnovel" / "state.json"
    if not state_path.is_file():
        return {"success": False, "error": "目标路径不是有效的网文项目"}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if "project_info" not in state:
            state["project_info"] = {}
        state["project_info"]["title"] = new_title
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"success": True, "project_root": str(target)}
    except (json.JSONDecodeError, OSError) as e:
        return {"success": False, "error": str(e)}


def cleanup_registry() -> dict:
    """清理注册表中已不存在的目录。"""
    registry = _read_workspaces()
    removed = []
    workspaces = registry.get("workspaces", {})
    for key in list(workspaces.keys()):
        project_root = Path(workspaces[key].get("current_project_root", workspaces[key].get("workspace_root", "")))
        if not project_root.exists():
            del workspaces[key]
            removed.append(str(project_root))
    # 如果 current 被清理了，重置
    current = registry.get("last_used_project_root")
    if current and not Path(current).exists():
        registry["last_used_project_root"] = None
    _write_workspaces(registry)
    return {"success": True, "removed": removed}
