"""集成测试：4 个菜单页面（总览 / 大纲 / 设定 / 章节）核心 API 交互。

测试策略：
- 复用 test_phase1_contracts 的 request_json + make_project 工具
- 每个菜单一个 test 函数，验证前端渲染该页面所需的全部 API
- 不测试 UI，只验证前后端数据契约
"""

from __future__ import annotations

import json
import sqlite3
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


# ---------------------------------------------------------------------------
# 辅助：创建带数据库的测试项目（设定页需要 index.db）
# ---------------------------------------------------------------------------

def make_project_with_db(
    tmp_path: Path,
    *,
    title: str = "测试小说",
    genre: str = "玄幻",
    target_chapters: int = 200,
) -> Path:
    """创建测试项目目录，含 index.db 和基础数据。"""
    project_root = tmp_path / "demo-project"
    webnovel_dir = project_root / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)

    (webnovel_dir / "state.json").write_text(
        json.dumps(
            {
                "project_info": {
                    "title": title,
                    "genre": genre,
                    "target_words": 500000,
                    "target_chapters": target_chapters,
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
        (project_root / folder).mkdir(exist_ok=True)

    # 章节文件
    (project_root / "正文" / "第001章.md").write_text("第一章正文内容", encoding="utf-8")
    (project_root / "正文" / "第002章.md").write_text("第二章正文内容", encoding="utf-8")

    # 大纲文件
    (project_root / "大纲" / "总纲.md").write_text("# 总纲\n\n故事主线", encoding="utf-8")
    (project_root / "大纲" / "卷一.md").write_text("# 卷一\n\n详细卷纲", encoding="utf-8")

    # 设定文件
    (project_root / "设定集" / "主角.md").write_text("# 主角\n\n姓名：林凡", encoding="utf-8")
    (project_root / "设定集" / "天剑宗.md").write_text("# 天剑宗\n\n修仙宗门", encoding="utf-8")

    # 创建 index.db
    db_path = webnovel_dir / "index.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            canonical_name TEXT NOT NULL,
            tier TEXT DEFAULT '装饰',
            desc TEXT,
            current_json TEXT,
            first_appearance INTEGER DEFAULT 0,
            last_appearance INTEGER DEFAULT 0,
            is_protagonist INTEGER DEFAULT 0,
            is_archived INTEGER DEFAULT 0,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS chapters (
            chapter INTEGER PRIMARY KEY,
            title TEXT,
            location TEXT,
            word_count INTEGER,
            characters TEXT,
            summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS relationships (
            id TEXT PRIMARY KEY,
            from_entity TEXT NOT NULL,
            to_entity TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            chapter INTEGER DEFAULT 0,
            desc TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # 插入测试实体
    conn.execute(
        "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("林凡", "角色", "林凡", "核心", "主角，修仙者", "{}", 1, 12, 1, 0, None, None),
    )
    conn.execute(
        "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("天剑宗", "势力", "天剑宗", "重要", "主角所在宗门", "{}", 1, 12, 0, 0, None, None),
    )
    conn.execute(
        "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("青云峰", "地点", "青云峰", "装饰", "修炼圣地", "{}", 1, 5, 0, 0, None, None),
    )
    # 插入测试章节
    conn.execute(
        "INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)",
        (1, "初入修仙", "正文/第001章.md", 3000, "[]", "林凡进入修仙界", None),
    )
    conn.execute(
        "INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)",
        (2, "拜师学艺", "正文/第002章.md", 3500, "[]", "林凡拜师天剑宗", None),
    )
    # 插入关系
    conn.execute(
        "INSERT INTO relationships VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("rel-1", "林凡", "天剑宗", "所属", 1, "林凡加入天剑宗", None),
    )
    conn.commit()
    conn.close()

    return project_root


# ===========================================================================
# ① 总览页 (Overview)
# ===========================================================================

def test_overview_page_apis(tmp_path: Path) -> None:
    """总览页加载所需 API：summary + recent-activity + projects。"""
    app = create_app(make_project_with_db(tmp_path))

    # GET /api/workbench/summary
    status, payload = request_json(app, "GET", "/api/workbench/summary")
    assert status == 200
    assert payload["pages"] == ["overview", "chapters", "outline", "settings"]
    assert payload["project"]["title"] == "测试小说"
    assert payload["project"]["genre"] == "玄幻"
    assert payload["progress"]["current_chapter"] == 12
    assert payload["progress"]["total_words"] == 88000
    assert "workspace_roots" in payload
    assert "workspaces" in payload

    # GET /api/recent-activity
    status, payload = request_json(app, "GET", "/api/recent-activity")
    assert status == 200
    assert isinstance(payload["activities"], list)

    # GET /api/projects
    status, payload = request_json(app, "GET", "/api/projects")
    assert status == 200
    assert "projects" in payload
    assert isinstance(payload["projects"], list)
    assert "current" in payload


# ===========================================================================
# ② 大纲页 (Outline)
# ===========================================================================

def test_outline_page_apis(tmp_path: Path) -> None:
    """大纲页加载所需 API：outline/tree + files/read + files/save。"""
    project_root = make_project_with_db(tmp_path)
    app = create_app(project_root)

    # GET /api/outline/tree
    status, payload = request_json(app, "GET", "/api/outline/tree")
    assert status == 200
    assert isinstance(payload["files"], list)
    assert isinstance(payload["volumes"], list)
    assert isinstance(payload["total_volumes"], int)

    # GET /api/files/read — 读取总纲
    status, payload = request_json(
        app, "GET", "/api/files/read", params={"path": "大纲/总纲.md"}
    )
    assert status == 200
    assert "content" in payload
    assert "故事主线" in payload["content"]

    # POST /api/files/save — 保存卷纲
    status, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": "大纲/卷二.md", "content": "# 卷二\n\n新卷纲"},
    )
    assert status == 200
    assert payload["path"] == "大纲/卷二.md"
    saved = project_root / "大纲" / "卷二.md"
    assert saved.read_text(encoding="utf-8") == "# 卷二\n\n新卷纲"


# ===========================================================================
# ③ 设定页 (Settings)
# ===========================================================================

def test_settings_page_apis(tmp_path: Path) -> None:
    """设定页加载所需 API：entities + files/read + files/save + query/*。"""
    project_root = make_project_with_db(tmp_path)
    app = create_app(project_root)

    # GET /api/entities
    status, payload = request_json(app, "GET", "/api/entities")
    assert status == 200
    assert isinstance(payload, list)
    assert len(payload) >= 3
    # 验证实体字段
    for entity in payload:
        assert "id" in entity
        assert "type" in entity
        assert "canonical_name" in entity

    # GET /api/entities?type=角色 — 按类型过滤
    status, payload = request_json(
        app, "GET", "/api/entities", params={"type": "角色"}
    )
    assert status == 200
    assert len(payload) >= 1
    assert all(e["type"] == "角色" for e in payload)

    # GET /api/relationships
    status, payload = request_json(app, "GET", "/api/relationships")
    assert status == 200
    assert isinstance(payload, list)

    # GET /api/files/read — 读取设定文件
    status, payload = request_json(
        app, "GET", "/api/files/read", params={"path": "设定集/主角.md"}
    )
    assert status == 200
    assert "林凡" in payload["content"]

    # POST /api/files/save — 修改设定
    status, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": "设定集/主角.md", "content": "# 主角\n\n姓名：林凡\n年龄：18"},
    )
    assert status == 200
    saved = project_root / "设定集" / "主角.md"
    assert "年龄：18" in saved.read_text(encoding="utf-8")

    # GET /api/query/foreshadowing
    status, payload = request_json(app, "GET", "/api/query/foreshadowing")
    assert status == 200

    # GET /api/query/golden-finger
    status, payload = request_json(app, "GET", "/api/query/golden-finger")
    assert status == 200

    # GET /api/query/rhythm
    status, payload = request_json(app, "GET", "/api/query/rhythm")
    assert status == 200

    # GET /api/query/debt
    status, payload = request_json(app, "GET", "/api/query/debt")
    assert status == 200


# ===========================================================================
# ④ 章节页 (Chapters)
# ===========================================================================

def test_chapters_page_apis(tmp_path: Path) -> None:
    """章节页加载所需 API：files/tree + files/read + files/save。"""
    project_root = make_project_with_db(tmp_path)
    app = create_app(project_root)

    # GET /api/files/tree — 获取文件树
    status, payload = request_json(app, "GET", "/api/files/tree")
    assert status == 200
    assert "正文" in payload
    assert isinstance(payload["正文"], list)
    # 应该包含第001章和第002章
    chapter_names = []
    for node in payload["正文"]:
        if node["type"] == "file":
            chapter_names.append(node["name"])
    assert "第001章.md" in chapter_names
    assert "第002章.md" in chapter_names

    # GET /api/files/read — 读取章节内容
    status, payload = request_json(
        app, "GET", "/api/files/read", params={"path": "正文/第001章.md"}
    )
    assert status == 200
    assert "第一章正文内容" in payload["content"]

    # POST /api/files/save — 保存章节
    status, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": "正文/第001章.md", "content": "修改后的第一章内容"},
    )
    assert status == 200
    saved = project_root / "正文" / "第001章.md"
    assert saved.read_text(encoding="utf-8") == "修改后的第一章内容"

    # POST /api/files/save — 创建新章节
    status, payload = request_json(
        app,
        "POST",
        "/api/files/save",
        {"path": "正文/第003章.md", "content": "第三章内容"},
    )
    assert status == 200
    assert (project_root / "正文" / "第003章.md").exists()


# ===========================================================================
# ⑤ 跨页面导航一致性
# ===========================================================================

def test_page_navigation_consistency(tmp_path: Path) -> None:
    """验证所有页面共享的 summary API 数据一致性。"""
    app = create_app(make_project_with_db(tmp_path))

    status, payload = request_json(app, "GET", "/api/workbench/summary")
    assert status == 200

    # 所有页面都依赖这些字段
    assert "project" in payload
    assert "progress" in payload
    assert "workspaces" in payload

    # project 字段
    project = payload["project"]
    assert project["title"] == "测试小说"
    assert project["genre"] == "玄幻"

    # progress 字段
    progress = payload["progress"]
    assert progress["current_chapter"] == 12
    assert progress["total_words"] == 88000

    # workspaces 包含三大目录
    workspaces = payload["workspaces"]
    assert "chapters" in workspaces
    assert "outline" in workspaces
    assert "settings" in workspaces


# ===========================================================================
# ⑥ 边界：空项目状态
# ===========================================================================

def test_overview_with_empty_project(tmp_path: Path) -> None:
    """无项目时 summary 返回空状态，不报错。"""
    # 创建一个没有 .webnovel 的空目录
    empty_root = tmp_path / "empty-project"
    empty_root.mkdir()
    app = create_app(empty_root)

    status, payload = request_json(app, "GET", "/api/workbench/summary")
    assert status == 200
    # 空项目时应该返回降级数据
    assert "project" in payload
    assert "progress" in payload


def test_chapters_empty_workspace(tmp_path: Path) -> None:
    """正文目录为空时 files/tree 返回空列表。"""
    project_root = make_project_with_db(tmp_path)
    # 清空正文目录
    for f in (project_root / "正文").iterdir():
        f.unlink()
    app = create_app(project_root)

    status, payload = request_json(app, "GET", "/api/files/tree")
    assert status == 200
    assert payload["正文"] == []
