"""Tests for QueryService — TDD for Task 501.

Tests the foreshadowing query logic.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
import sys
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.query_service import QueryService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with .webnovel directory."""
    webnovel = tmp_path / ".webnovel"
    webnovel.mkdir()
    return tmp_path


def write_state(project_root: Path, data: dict) -> None:
    """Helper to write state.json."""
    state_path = project_root / ".webnovel" / "state.json"
    state_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Happy path: 5 foreshadowing items, sorted by urgency, by_tier classified
# ---------------------------------------------------------------------------

def test_query_foreshadowing_happy_path(temp_project):
    """state.json 有 5 条伏笔 → query_foreshadowing 返回 5 条 → 按紧急度排序 → by_tier 分类正确."""
    write_state(temp_project, {
        "last_written_chapter": 15,
        "foreshadowing": [
            {"id": "fs1", "plant_chapter": 5, "reveal_chapter": 20, "status": "planted", "weight": 1.0, "title": "项链的秘密"},
            {"id": "fs2", "plant_chapter": 5, "reveal_chapter": 25, "status": "planted", "weight": 1.0, "title": "父亲的遗言"},
            {"id": "fs3", "plant_chapter": 3, "reveal_chapter": 6,  "status": "planted", "weight": 1.0, "title": "第三章伏笔"},
            {"id": "fs4", "plant_chapter": 1, "reveal_chapter": 10, "status": "revealed", "weight": 1.0, "title": "已揭示"},
            {"id": "fs5", "plant_chapter": 2, "reveal_chapter": 40, "status": "planted", "weight": 0.5, "title": "长期伏笔"},
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    # 5 条结果
    assert result["stats"]["total"] == 5
    assert len(result["foreshadowing"]) == 5

    # 按紧急度降序排序
    urgencies = [r["urgency"] for r in result["foreshadowing"]]
    assert urgencies == sorted(urgencies, reverse=True)

    # 统计
    assert result["stats"]["planted"] == 4
    assert result["stats"]["revealed"] == 1
    assert result["stats"]["recovery_rate"] == pytest.approx(1 / 5)

    # by_tier 分类
    by_tier = result["by_tier"]
    assert len(by_tier["chapter"]) == 1   # payoff_window <= 5 (fs3: 3)
    assert len(by_tier["volume"]) == 3   # 5 < payoff_window <= 30 (fs1: 15, fs2: 20, fs4: 9)
    assert len(by_tier["book"]) == 1     # payoff_window > 30 (fs5: 38)

    # 各条目的 tier 字段
    fs1 = next(r for r in result["foreshadowing"] if r["id"] == "fs1")
    assert fs1["tier"] == "volume"
    assert fs1["payoff_window"] == 15

    fs3 = next(r for r in result["foreshadowing"] if r["id"] == "fs3")
    assert fs3["tier"] == "chapter"
    assert fs3["payoff_window"] == 3


# ---------------------------------------------------------------------------
# Edge case 1: current_chapter > reveal_chapter → urgency=1.0 → urgency_level="critical"
# ---------------------------------------------------------------------------

def test_query_foreshadowing_overdue_is_critical(temp_project):
    """current_chapter > reveal_chapter → urgency=1.0 → urgency_level="critical"."""
    write_state(temp_project, {
        "last_written_chapter": 50,
        "foreshadowing": [
            {"id": "overdue1", "plant_chapter": 5, "reveal_chapter": 20, "status": "planted", "weight": 1.0},
            {"id": "overdue2", "plant_chapter": 1, "reveal_chapter": 10, "status": "planted", "weight": 0.5},
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    # 当前章节 50，已远超所有 reveal_chapter， urgency 都应为 1.0
    for r in result["foreshadowing"]:
        assert r["urgency"] == 1.0
        assert r["urgency_level"] == "critical"

    # overdue 统计应为 2
    assert result["stats"]["overdue"] == 2


# ---------------------------------------------------------------------------
# Edge case 2: status="revealed" → urgency=0.0 → urgency_level="normal"
# ---------------------------------------------------------------------------

def test_query_foreshadowing_revealed_urgency_zero(temp_project):
    """status="revealed" → urgency=0.0 → urgency_level="normal"."""
    write_state(temp_project, {
        "last_written_chapter": 100,
        "foreshadowing": [
            {"id": "fs_a", "plant_chapter": 5, "reveal_chapter": 20, "status": "revealed", "weight": 2.0},
            {"id": "fs_b", "plant_chapter": 1, "reveal_chapter": 3,  "status": "revealed", "weight": 1.0},
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    for r in result["foreshadowing"]:
        assert r["urgency"] == 0.0
        assert r["urgency_level"] == "normal"
        assert r["status"] == "revealed"

    assert result["stats"]["revealed"] == 2
    assert result["stats"]["recovery_rate"] == 1.0


# ---------------------------------------------------------------------------
# Error case: state.json 不存在 → 返回空列表，stats 全为 0
# ---------------------------------------------------------------------------

def test_query_foreshadowing_no_state_file(temp_project):
    """state.json 不存在 → 返回空列表，stats 全为 0."""
    # No write_state call — state.json does not exist
    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    assert result["foreshadowing"] == []
    stats = result["stats"]
    assert stats["total"] == 0
    assert stats["planted"] == 0
    assert stats["revealed"] == 0
    assert stats["overdue"] == 0
    assert stats["recovery_rate"] == 0.0
    assert result["by_tier"] == {"chapter": [], "volume": [], "book": []}


# ---------------------------------------------------------------------------
# Error case: state.json is malformed JSON → returns empty list
# ---------------------------------------------------------------------------

def test_query_foreshadowing_malformed_state(temp_project):
    """state.json is malformed JSON → returns empty list."""
    state_path = temp_project / ".webnovel" / "state.json"
    state_path.write_text("{ not valid json }", encoding="utf-8")

    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    assert result["foreshadowing"] == []
    assert result["stats"]["total"] == 0


# ---------------------------------------------------------------------------
# Edge case: missing optional fields in foreshadowing item → defaults
# ---------------------------------------------------------------------------

def test_query_foreshadowing_missing_optional_fields(temp_project):
    """Missing optional fields → use defaults."""
    write_state(temp_project, {
        "last_written_chapter": 10,
        "foreshadowing": [
            {"id": "fs1"},  # no plant_chapter, reveal_chapter, status, weight
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    fs = result["foreshadowing"][0]
    assert fs["plant_chapter"] == 0        # default
    assert fs["reveal_chapter"] == 10      # default: plant_chapter + 10 = 0 + 10
    assert fs["weight"] == 1.0            # default
    assert fs["status"] == "planted"      # default
    assert fs["tier"] == "volume"        # payoff_window=10 → 5 < 10 <= 30 → volume
    assert fs["payoff_window"] == 10


# ---------------------------------------------------------------------------
# chapters_remaining calculation
# ---------------------------------------------------------------------------

def test_query_foreshadowing_chapters_remaining(temp_project):
    """chapters_remaining = reveal_chapter - current_chapter (clamped to 0)."""
    write_state(temp_project, {
        "last_written_chapter": 12,
        "foreshadowing": [
            {"id": "fs1", "plant_chapter": 5, "reveal_chapter": 20, "status": "planted"},
            {"id": "fs2", "plant_chapter": 5, "reveal_chapter": 10, "status": "planted"},  # already past
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_foreshadowing()

    fs1 = next(r for r in result["foreshadowing"] if r["id"] == "fs1")
    assert fs1["chapters_remaining"] == 8  # 20 - 12

    fs2 = next(r for r in result["foreshadowing"] if r["id"] == "fs2")
    assert fs2["chapters_remaining"] == 0  # clamped to 0
