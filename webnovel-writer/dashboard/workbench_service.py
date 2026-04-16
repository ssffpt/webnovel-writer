"""Phase 1 workbench helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from .models import WORKBENCH_PAGES, WORKSPACE_ROOTS
from .path_guard import safe_resolve

_ALLOWED_ROOTS = tuple(WORKSPACE_ROOTS.values())


def load_project_summary(project_root: Path) -> dict[str, Any]:
    state_path = project_root / ".webnovel" / "state.json"
    state: dict[str, Any] = {}
    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))

    project_info = state.get("project_info") or {}
    progress = state.get("progress") or {}

    workspaces: dict[str, dict[str, Any]] = {}
    for page, root_name in WORKSPACE_ROOTS.items():
        folder = project_root / root_name
        file_count = sum(1 for path in folder.rglob("*") if path.is_file()) if folder.is_dir() else 0
        workspaces[page] = {
            "root": root_name,
            "exists": folder.is_dir(),
            "file_count": file_count,
        }

    return {
        "pages": list(WORKBENCH_PAGES),
        "project": {
            "title": project_info.get("title") or "未命名项目",
            "genre": project_info.get("genre"),
            "target_words": project_info.get("target_words"),
            "target_chapters": project_info.get("target_chapters"),
        },
        "progress": {
            "current_chapter": progress.get("current_chapter"),
            "current_volume": progress.get("current_volume"),
            "total_words": progress.get("total_words", 0),
        },
        "workspace_roots": list(_ALLOWED_ROOTS),
        "workspaces": workspaces,
        "recent_tasks": [],
        "recent_changes": [],
        "next_suggestions": [],
    }


def save_workspace_file(project_root: Path, relative_path: str, content: str) -> dict[str, Any]:
    resolved = safe_resolve(project_root, relative_path)
    allowed_parents = [project_root / name for name in _ALLOWED_ROOTS]
    if not any(_is_child(resolved, parent) for parent in allowed_parents):
        raise HTTPException(status_code=403, detail="仅允许写入 正文/大纲/设定集 目录下的文件")

    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
    stat = resolved.stat()
    return {
        "path": relative_path,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "size": stat.st_size,
    }


def build_chat_response(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    text = (message or "").strip()
    context = context or {}
    page = context.get("page")
    selected_path = context.get("selectedPath")
    dirty = bool(context.get("dirty"))

    action: dict[str, Any] | None = None
    reply = "我先帮你整理成一个可执行动作。"
    reason = "根据当前聊天内容生成建议动作。"

    if dirty:
        return {
            "reply": "你当前页面有未保存修改，建议先保存再执行高风险动作。",
            "suggested_actions": [],
            "reason": "检测到当前页面存在未保存改动，优先避免执行可能覆盖结果的动作。",
            "scope": {
                "page": page,
                "selectedPath": selected_path,
            },
        }

    if any(keyword in text for keyword in ("规划", "卷纲", "章纲", "大纲")):
        action = {
            "type": "plan_outline",
            "label": "生成当前卷纲",
            "params": {"path": selected_path},
        }
        reply = "我已识别为大纲规划需求。"
        reason = "消息中包含规划/卷纲/章纲等关键词，优先匹配大纲规划动作。"
    elif any(keyword in text for keyword in ("设定", "人物", "世界观")):
        action = {
            "type": "inspect_setting",
            "label": "检查当前设定冲突",
            "params": {"path": selected_path},
        }
        reply = "我已识别为设定检查需求。"
        reason = "消息中包含设定/人物/世界观等关键词，优先匹配设定检查动作。"
    elif any(keyword in text for keyword in ("审查", "检查章节", "检查")):
        action = {
            "type": "review_chapter",
            "label": "审查当前章节",
            "params": {"path": selected_path},
        }
        reply = "我已识别为章节审查需求。"
        reason = "消息中包含审查/检查等关键词，优先匹配章节审查动作。"
    elif any(keyword in text for keyword in ("写", "生成章节", "续写")):
        action = {
            "type": "write_chapter",
            "label": "生成当前章节",
            "params": {"path": selected_path},
        }
        reply = "我已识别为章节写作需求。"
        reason = "消息中包含写/生成章节/续写等关键词，优先匹配章节写作动作。"
    elif text in {"继续", "帮我继续", "继续吧", "继续一下"}:
        if page == "outline":
            action = {
                "type": "plan_outline",
                "label": "生成当前卷纲",
                "params": {"path": selected_path},
            }
            reply = "我会优先继续当前大纲规划。"
            reason = "当前位于大纲页，且你希望继续，因此优先推荐大纲规划动作。"
        elif page == "chapters":
            action = {
                "type": "write_chapter",
                "label": "生成当前章节",
                "params": {"path": selected_path},
            }
            reply = "我会优先继续当前章节写作。"
            reason = "当前位于章节页，且你希望继续，因此优先推荐章节写作动作。"
        elif page == "settings":
            action = {
                "type": "inspect_setting",
                "label": "检查当前设定冲突",
                "params": {"path": selected_path},
            }
            reply = "我会优先继续当前设定检查。"
            reason = "当前位于设定页，且你希望继续，因此优先推荐设定检查动作。"

    return {
        "reply": reply,
        "suggested_actions": [action] if action else [],
        "reason": reason,
        "scope": {
            "page": page,
            "selectedPath": selected_path,
        },
    }


def _is_child(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def build_outline_tree(project_root: Path) -> dict[str, Any]:
    """构建大纲树结构。

    大纲目录为平铺结构（非子目录）：
    - 大纲/总纲.md
    - 大纲/爽点规划.md
    - 大纲/第N卷-详细大纲.md

    返回 { files, volumes, total_volumes }。
    """
    import re

    outline_dir = project_root / "大纲"

    # 扫描所有 .md 文件
    files: list[dict] = []
    if outline_dir.is_dir():
        for f in sorted(outline_dir.iterdir()):
            if f.is_file() and f.suffix == ".md":
                files.append({
                    "name": f.name,
                    "path": f"大纲/{f.name}",
                    "type": "file",
                })

    # 从 state.json 读取 target_chapters
    target_chapters = 600  # 默认
    state_path = project_root / ".webnovel" / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            tc = state.get("project_info", {}).get("target_chapters")
            if tc and isinstance(tc, (int, float)):
                target_chapters = int(tc)
        except (json.JSONDecodeError, OSError):
            pass

    # 每卷 50 章
    chapters_per_volume = 50
    total_volumes = (target_chapters - 1) // chapters_per_volume + 1 if target_chapters > 0 else 1

    # 检测每卷是否有详细大纲
    volume_pattern = re.compile(r"第(\d+)卷")
    existing_volumes: set[int] = set()
    for f in files:
        m = volume_pattern.search(f["name"])
        if m:
            existing_volumes.add(int(m.group(1)))

    volumes: list[dict] = []
    for v in range(1, total_volumes + 1):
        start = (v - 1) * chapters_per_volume + 1
        end = min(v * chapters_per_volume, target_chapters)
        has_outline = v in existing_volumes
        outline_path = f"大纲/第{v}卷-详细大纲.md" if has_outline else None
        volumes.append({
            "number": v,
            "has_outline": has_outline,
            "outline_path": outline_path,
            "chapter_range": [start, end],
        })

    return {
        "files": files,
        "volumes": volumes,
        "total_volumes": total_volumes,
    }
