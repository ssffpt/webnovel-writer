"""Tests for ReviewStorage — Task 403 TDD."""
from __future__ import annotations

import asyncio
import json
import sys
import sqlite3
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_handlers.review_storage import ReviewStorage


def _storage(project_root: str) -> ReviewStorage:
    return ReviewStorage(project_root)


# ---------------------------------------------------------------------------
# Happy path: save_metrics → writes to index.db
# ---------------------------------------------------------------------------

def test_save_metrics_creates_tables_and_inserts_rows():
    """save_metrics creates review_metrics + review_sessions tables and inserts rows."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = _storage(tmpdir)

        chapter_results = {
            1: [
                {"dimension": "爽点密度", "score": 7.5, "issues": [{"severity": "medium", "message": "开头缺钩子"}]},
                {"dimension": "设定一致性", "score": 8.0, "issues": []},
            ],
            2: [
                {"dimension": "爽点密度", "score": 6.5, "issues": [{"severity": "high", "message": "章末缺钩子"}]},
                {"dimension": "设定一致性", "score": 7.0, "issues": []},
            ],
        }
        summary = {"avg_score": 7.25, "total_issues": 2}

        result = storage.save_metrics(chapter_results, summary)

        assert result["metrics_saved"] is True
        assert result["session_id"] is not None

        # Verify DB contents
        conn = sqlite3.connect(str(storage.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM review_metrics ORDER BY chapter, dimension")
        rows = cursor.fetchall()
        assert len(rows) == 4  # 2 chapters x 2 dimensions

        cursor.execute("SELECT * FROM review_sessions")
        session = cursor.fetchone()
        assert session["chapter_start"] == 1
        assert session["chapter_end"] == 2
        assert session["avg_score"] == 7.25
        assert session["total_issues"] == 2

        conn.close()


def test_save_metrics_auto_creates_db_directory():
    """index.db parent directory does not exist → auto-created."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = _storage(tmpdir)
        # .webnovel dir should not exist yet
        assert not (Path(tmpdir) / ".webnovel").exists()

        storage.save_metrics({1: []}, {"avg_score": 0, "total_issues": 0})

        assert storage.db_path.exists()


# ---------------------------------------------------------------------------
# Happy path: writeback_state → updates state.json
# ---------------------------------------------------------------------------

def test_writeback_state_creates_state_json():
    """writeback_state creates state.json if it does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = _storage(tmpdir)
        state_path = Path(tmpdir) / ".webnovel" / "state.json"

        assert not state_path.exists()

        chapter_results = {
            1: [
                {"dimension": "爽点密度", "score": 7.5},
                {"dimension": "设定一致性", "score": 8.0},
            ],
        }

        result = storage.writeback_state(chapter_results)

        assert result["state_updated"] is True
        assert result["chapters_updated"] == [1]
        assert state_path.exists()

        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert "1" in state["chapters"]
        assert state["chapters"]["1"]["review_score"] == 7.8  # rounded from 7.75
        assert "reviewed_at" in state["chapters"]["1"]
        assert state["chapters"]["1"]["review_dimensions"]["爽点密度"] == 7.5


def test_writeback_state_merges_into_existing_state():
    """writeback_state merges into existing state.json, does not overwrite other fields."""
    with tempfile.TemporaryDirectory() as tmpdir:
        webnovel_dir = Path(tmpdir) / ".webnovel"
        webnovel_dir.mkdir(parents=True, exist_ok=True)
        state_path = webnovel_dir / "state.json"

        existing_state = {
            "chapters": {
                "1": {"title": "第一章", "word_count": 3000},
                "2": {"title": "第二章", "word_count": 3500},
            },
            "project_meta": {"name": "test novel"},
        }
        state_path.write_text(json.dumps(existing_state, ensure_ascii=False), encoding="utf-8")

        storage = _storage(tmpdir)
        chapter_results = {
            3: [{"dimension": "爽点密度", "score": 6.0}],
        }

        result = storage.writeback_state(chapter_results)

        state = json.loads(state_path.read_text(encoding="utf-8"))
        # Existing chapter 1, 2 preserved
        assert state["chapters"]["1"]["title"] == "第一章"
        assert state["chapters"]["1"]["word_count"] == 3000
        # New chapter 3 added
        assert "3" in state["chapters"]
        assert state["chapters"]["3"]["review_score"] == 6.0
        # project_meta preserved
        assert state["project_meta"]["name"] == "test novel"


# ---------------------------------------------------------------------------
# Edge case 1: avg_score >= 8.5 → verdict="优秀"
# ---------------------------------------------------------------------------

def test_get_verdict_excellent():
    """avg_score >= 8.5 returns '优秀'."""
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    handler = ReviewSkillHandler()

    assert handler._get_verdict(8.5) == "优秀"
    assert handler._get_verdict(9.0) == "优秀"
    assert handler._get_verdict(10.0) == "优秀"


def test_get_verdict_good():
    """7.0 <= avg_score < 8.5 returns '良好'."""
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    handler = ReviewSkillHandler()

    assert handler._get_verdict(7.0) == "良好"
    assert handler._get_verdict(7.5) == "良好"
    assert handler._get_verdict(8.4) == "良好"


def test_get_verdict_passing():
    """6.0 <= avg_score < 7.0 returns '合格'."""
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    handler = ReviewSkillHandler()

    assert handler._get_verdict(6.0) == "合格"
    assert handler._get_verdict(6.5) == "合格"
    assert handler._get_verdict(6.9) == "合格"


def test_get_verdict_needs_revision():
    """avg_score < 6.0 returns '需要修改'."""
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    handler = ReviewSkillHandler()

    assert handler._get_verdict(5.9) == "需要修改"
    assert handler._get_verdict(3.0) == "需要修改"
    assert handler._get_verdict(0.0) == "需要修改"


# ---------------------------------------------------------------------------
# Edge case 2: index.db not exist → auto-create tables and file
# ---------------------------------------------------------------------------

def test_save_metrics_creates_db_when_missing():
    """save_metrics called when index.db missing → creates file and tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = _storage(tmpdir)
        assert not storage.db_path.exists()

        storage.save_metrics({1: [{"dimension": "爽点密度", "score": 7.0, "issues": []}]}, {"avg_score": 7.0, "total_issues": 0})

        assert storage.db_path.exists()

        conn = sqlite3.connect(str(storage.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        assert "review_metrics" in tables
        assert "review_sessions" in tables


# ---------------------------------------------------------------------------
# Error case: state.json malformed → overwrite with valid data, no crash
# ---------------------------------------------------------------------------

def test_writeback_state_malformed_state_json_no_crash():
    """Malformed existing state.json → overwrites with clean data, does not crash."""
    with tempfile.TemporaryDirectory() as tmpdir:
        webnovel_dir = Path(tmpdir) / ".webnovel"
        webnovel_dir.mkdir(parents=True, exist_ok=True)
        state_path = webnovel_dir / "state.json"
        state_path.write_text("{ invalid json }", encoding="utf-8")

        storage = _storage(tmpdir)
        chapter_results = {1: [{"dimension": "爽点密度", "score": 7.5, "issues": []}]}

        # Must not raise
        result = storage.writeback_state(chapter_results)

        assert result["state_updated"] is True
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert "chapters" in state
        assert "1" in state["chapters"]


# ---------------------------------------------------------------------------
# generate_suggestions
# ---------------------------------------------------------------------------

def test_generate_suggestions_low_dimensions():
    """_generate_suggestions returns suggestions for dimensions below threshold."""
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    handler = ReviewSkillHandler()

    summary = {
        "dimension_avg": {
            "爽点密度": 5.0,
            "设定一致性": 7.0,
            "节奏比例": 4.0,
            "人物OOC": 8.0,
            "叙事连贯性": 5.5,
            "追读力": 5.0,
        }
    }

    suggestions = handler._generate_suggestions(summary)

    assert "增加情节转折和情绪波动，提升爽点密度" in suggestions
    assert "调整对话/描写/动作比例，避免大段纯叙述" in suggestions
    assert "检查前后文逻辑，消除跳跃和矛盾" in suggestions
    assert "强化章末钩子，增加悬念和期待感" in suggestions
    # 设定一致性 and 人物OOC are above threshold
    assert not any("设定一致性" in s for s in suggestions)
    assert not any("人物OOC" in s for s in suggestions)


# ---------------------------------------------------------------------------
# Step 4: _generate_report happy path
# ---------------------------------------------------------------------------

def test_generate_report_includes_overall_chapters_priority_fixes_suggestions():
    """_generate_report returns report with overall, chapters, priority_fixes, suggestions."""
    from dashboard.skill_handlers.review_handler import ReviewSkillHandler
    handler = ReviewSkillHandler()

    context = {
        "review_summary": {
            "avg_score": 7.5,
            "dimension_avg": {"爽点密度": 7.0, "设定一致性": 8.0},
            "total_issues": 3,
            "critical_issues": [{"severity": "critical", "message": "设定矛盾"}],
            "high_issues": [{"severity": "high", "message": "章末缺钩子"}],
        },
        "all_chapter_results": {
            1: [
                {"dimension": "爽点密度", "score": 7.0, "issues": [{"severity": "high", "message": "缺钩子"}]},
                {"dimension": "设定一致性", "score": 8.0, "issues": []},
            ],
        },
    }

    result = asyncio.run(handler._generate_report(context))

    assert "report" in result
    assert result["instruction"] == "请确认审查报告"
    report = result["report"]
    assert report["overall"]["avg_score"] == 7.5
    assert report["overall"]["verdict"] == "良好"
    assert report["overall"]["dimension_scores"]["爽点密度"] == 7.0
    assert 1 in report["chapters"]
    assert report["chapters"][1]["score"] == 7.5
    assert len(report["priority_fixes"]) == 2  # critical + high
    assert "review_report" in context  # context updated with report
