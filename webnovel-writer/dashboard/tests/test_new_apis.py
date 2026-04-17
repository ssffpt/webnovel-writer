"""契约测试：新增 7 个 API（TDD 红灯阶段）。

参照 test_phase1_contracts.py 的模式，使用 ASGI raw scope 直接调用 FastAPI app。
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO_WEBNOVEL_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_WEBNOVEL_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_WEBNOVEL_ROOT))

from dashboard.app import create_app  # noqa: E402
from dashboard.tests.test_phase1_contracts import request_json  # noqa: E402


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def make_project(
    tmp_path: Path,
    *,
    title: str = "测试小说",
    genre: str = "玄幻",
    target_chapters: int = 200,
    with_db: bool = False,
) -> Path:
    """创建测试项目目录，可选创建 index.db。"""
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

    (project_root / "正文" / "第001章.md").write_text("旧正文", encoding="utf-8")
    (project_root / "大纲" / "总纲.md").write_text("# 总纲", encoding="utf-8")
    (project_root / "设定集" / "主角.md").write_text("旧设定", encoding="utf-8")

    if with_db:
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
        # 插入测试章节
        conn.execute(
            "INSERT INTO chapters VALUES (?, ?, ?, ?, ?, ?, ?)",
            (1, "初入修仙", "正文/第001章.md", 3000, "[]", "林凡进入修仙界", None),
        )
        conn.commit()
        conn.close()

    return project_root


# ---------------------------------------------------------------------------
# GET /api/genres
# ---------------------------------------------------------------------------

def test_genres_returns_200_with_list(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/genres")

    assert status == 200
    assert isinstance(payload["genres"], list)
    assert len(payload["genres"]) > 0


def test_genres_each_item_has_key_and_label(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/genres")

    assert status == 200
    for item in payload["genres"]:
        assert "key" in item, f"missing 'key' in {item}"
        assert "label" in item, f"missing 'label' in {item}"
        assert isinstance(item["key"], str)
        assert isinstance(item["label"], str)


def test_genres_contains_xuanhuan_and_rules_mystery(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/genres")

    assert status == 200
    keys = [g["key"] for g in payload["genres"]]
    assert "xuanhuan" in keys, f"'xuanhuan' not in {keys}"
    assert "rules-mystery" in keys, f"'rules-mystery' not in {keys}"


def test_genres_items_may_have_profile_id(tmp_path: Path) -> None:
    """每项可选包含 profile_id（str 或 null）。"""
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/genres")

    assert status == 200
    for item in payload["genres"]:
        if "profile_id" in item:
            assert item["profile_id"] is None or isinstance(item["profile_id"], str)


# ---------------------------------------------------------------------------
# GET /api/golden-finger-types
# ---------------------------------------------------------------------------

def test_golden_finger_types_returns_200_with_list(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/golden-finger-types")

    assert status == 200
    assert isinstance(payload["types"], list)


def test_golden_finger_types_contains_none_key(tmp_path: Path) -> None:
    """types 应包含 key='none' 的项（无金手指）。"""
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/golden-finger-types")

    assert status == 200
    keys = [t["key"] for t in payload["types"]]
    assert "none" in keys, f"'none' not in {keys}"


def test_golden_finger_types_each_item_has_key_and_label(tmp_path: Path) -> None:
    app = create_project_with_tmp(tmp_path)
    status, payload = request_json(app, "GET", "/api/golden-finger-types")

    assert status == 200
    for item in payload["types"]:
        assert "key" in item
        assert "label" in item
        assert isinstance(item["key"], str)
        assert isinstance(item["label"], str)


# ---------------------------------------------------------------------------
# GET /api/outline/tree
# ---------------------------------------------------------------------------

def test_outline_tree_returns_200_with_structure(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/outline/tree")

    assert status == 200
    assert isinstance(payload["files"], list)
    assert isinstance(payload["volumes"], list)
    assert isinstance(payload["total_volumes"], int)


def test_outline_tree_volumes_have_required_fields(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/outline/tree")

    assert status == 200
    for vol in payload["volumes"]:
        assert "number" in vol
        assert "has_outline" in vol
        assert isinstance(vol["has_outline"], bool)
        assert "chapter_range" in vol
        assert len(vol["chapter_range"]) == 2


# ---------------------------------------------------------------------------
# GET /api/recent-activity
# ---------------------------------------------------------------------------

def test_recent_activity_returns_200_with_activities_list(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/recent-activity")

    assert status == 200
    assert isinstance(payload["activities"], list)


# ---------------------------------------------------------------------------
# GET /api/projects
# ---------------------------------------------------------------------------

def test_projects_returns_200_with_projects_and_current(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(app, "GET", "/api/projects")

    assert status == 200
    assert "projects" in payload
    assert isinstance(payload["projects"], list)
    assert "current" in payload


# ---------------------------------------------------------------------------
# POST /api/project/create
# ---------------------------------------------------------------------------

def test_project_create_rejects_missing_title(tmp_path: Path) -> None:
    app = create_app(make_project(tmp_path))
    status, payload = request_json(
        app, "POST", "/api/project/create", {"genre": "修仙"},
    )

    assert status == 400


def test_project_create_success(tmp_path: Path) -> None:
    """正常创建项目：返回 success=true，项目目录存在且含 state.json。"""
    app = create_app(make_project(tmp_path))
    status, payload = request_json(
        app,
        "POST",
        "/api/project/create",
        {"title": "我的修仙小说", "genre": "修仙", "target_chapters": 600},
    )

    assert status == 200
    assert payload["success"] is True
    assert "project_root" in payload
    assert isinstance(payload["project_root"], str)
    assert "state" in payload

    # 验证项目目录实际存在
    project_root = Path(payload["project_root"])
    assert project_root.exists()
    assert (project_root / ".webnovel" / "state.json").is_file()


# ---------------------------------------------------------------------------
# POST /api/project/switch
# ---------------------------------------------------------------------------

def test_project_switch_rejects_invalid_path(tmp_path: Path) -> None:
    """目标路径不存在 .webnovel/state.json 时返回 400。"""
    app = create_app(make_project(tmp_path))
    status, payload = request_json(
        app, "POST", "/api/project/switch", {"path": "/nonexistent/path"},
    )

    assert status == 400


def test_project_switch_success(tmp_path: Path) -> None:
    """正常切换：返回 success=true。"""
    # 先创建两个项目
    project_a = make_project(tmp_path / "a", title="项目A")
    project_b = make_project(tmp_path / "b", title="项目B")

    app = create_app(project_a)
    status, payload = request_json(
        app, "POST", "/api/project/switch", {"path": str(project_b)},
    )

    assert status == 200
    assert payload["success"] is True
    assert payload["project_root"] == str(project_b)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------

def create_project_with_tmp(tmp_path: Path):
    """创建 app 的简写。"""
    return create_app(make_project(tmp_path))
