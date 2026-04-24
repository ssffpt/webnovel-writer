"""Tests for QueryService — TDD for Task 502: query_rhythm.

Tests the rhythm analysis query logic.
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


def write_rhythm(project_root: Path, data: dict) -> None:
    """Helper to write rhythm_data.json."""
    path = project_root / ".webnovel" / "rhythm_data.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Helper: compute expected pacing_label
# ---------------------------------------------------------------------------

def pacing_label(score: float) -> str:
    if score >= 0.7:
        return "快节奏"
    elif score >= 0.4:
        return "中等节奏"
    else:
        return "慢节奏"


# ---------------------------------------------------------------------------
# Test 1: No data → empty rhythm_data, success=True
# ---------------------------------------------------------------------------

def test_query_rhythm_no_file(temp_project):
    """rhythm_data.json 不存在 → 返回 success=True, rhythm_data={}."""
    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    assert result["success"] is True
    assert result["rhythm_data"] == {}


# ---------------------------------------------------------------------------
# Test 2: Single volume, happy path
# ---------------------------------------------------------------------------

def test_query_rhythm_single_volume(temp_project):
    """单卷节奏分析 → beat_distribution / avg_emotion_intensity / pacing_label / emotion_curve / climax_chapters 全部正确."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1, 2, 3, 4, 5],
            "beat_types": ["hook", "development", "climax", "climax", "resolution"],
            "emotion_intensity": [3, 5, 8, 9, 7],
            "pacing_score": 0.75,
        }
    })

    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    assert result["success"] is True
    vol = result["rhythm_data"]["volume_1"]

    # total_chapters
    assert vol["total_chapters"] == 5

    # beat_distribution
    assert vol["beat_distribution"] == {
        "hook": 1, "development": 1, "climax": 2, "resolution": 1,
        "setup": 0,
    }

    # avg_emotion_intensity
    assert vol["avg_emotion_intensity"] == pytest.approx((3 + 5 + 8 + 9 + 7) / 5)

    # pacing_score & pacing_label
    assert vol["pacing_score"] == 0.75
    assert vol["pacing_label"] == "快节奏"  # score >= 0.7

    # emotion_curve
    assert vol["emotion_curve"] == [
        {"chapter": 1, "intensity": 3},
        {"chapter": 2, "intensity": 5},
        {"chapter": 3, "intensity": 8},
        {"chapter": 4, "intensity": 9},
        {"chapter": 5, "intensity": 7},
    ]

    # climax_chapters: intensity >= 8
    assert vol["climax_chapters"] == [3, 4]


# ---------------------------------------------------------------------------
# Test 3: Multiple volumes → returns all
# ---------------------------------------------------------------------------

def test_query_rhythm_multiple_volumes(temp_project):
    """多卷时 query_rhythm() 返回所有卷数据."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1, 2, 3],
            "beat_types": ["hook", "development", "resolution"],
            "emotion_intensity": [2, 4, 6],
            "pacing_score": 0.5,
        },
        "volume_2": {
            "chapters": [1, 2, 3, 4],
            "beat_types": ["hook", "climax", "climax", "resolution"],
            "emotion_intensity": [3, 7, 9, 5],
            "pacing_score": 0.8,
        },
    })

    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    assert result["success"] is True
    assert set(result["rhythm_data"].keys()) == {"volume_1", "volume_2"}
    assert result["rhythm_data"]["volume_1"]["total_chapters"] == 3
    assert result["rhythm_data"]["volume_2"]["total_chapters"] == 4


# ---------------------------------------------------------------------------
# Test 4: Filter by volume_number
# ---------------------------------------------------------------------------

def test_query_rhythm_filter_by_volume(temp_project):
    """指定 volume_number → 只返回该卷数据."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1, 2],
            "beat_types": ["hook", "resolution"],
            "emotion_intensity": [2, 4],
            "pacing_score": 0.3,
        },
        "volume_2": {
            "chapters": [1, 2, 3],
            "beat_types": ["hook", "climax", "resolution"],
            "emotion_intensity": [3, 8, 5],
            "pacing_score": 0.9,
        },
    })

    service = QueryService(str(temp_project))

    # volume_number=1 → only volume_1
    result = service.query_rhythm(volume_number=1)
    assert result["success"] is True
    assert set(result["rhythm_data"].keys()) == {"volume_1"}

    # volume_number=2 → only volume_2
    result = service.query_rhythm(volume_number=2)
    assert result["success"] is True
    assert set(result["rhythm_data"].keys()) == {"volume_2"}

    # volume_number=99 → 不存在的卷 → 空结构
    result = service.query_rhythm(volume_number=99)
    assert result["success"] is True
    assert result["rhythm_data"] == {}


# ---------------------------------------------------------------------------
# Test 5: climax_chapters edge cases
# ---------------------------------------------------------------------------

def test_query_rhythm_climax_chapters_no_high_intensity(temp_project):
    """所有章节 intensity < 8 → climax_chapters 为空."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1, 2, 3],
            "beat_types": ["hook", "development", "resolution"],
            "emotion_intensity": [3, 5, 7],  # none >= 8
            "pacing_score": 0.4,
        }
    })

    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    assert result["rhythm_data"]["volume_1"]["climax_chapters"] == []


def test_query_rhythm_climax_chapters_exactly_8(temp_project):
    """章节 intensity == 8 → 应计入 climax_chapters."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1, 2, 3, 4],
            "beat_types": ["hook", "development", "climax", "resolution"],
            "emotion_intensity": [3, 8, 5, 2],  # chapter 2 has intensity==8
            "pacing_score": 0.5,
        }
    })

    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    assert result["rhythm_data"]["volume_1"]["climax_chapters"] == [2]


# ---------------------------------------------------------------------------
# Test 6: pacing_label boundary values
# ---------------------------------------------------------------------------

def test_query_rhythm_pacing_label_fast(temp_project):
    """pacing_score >= 0.7 → 快节奏."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1], "beat_types": ["hook"],
            "emotion_intensity": [5], "pacing_score": 0.7,
        }
    })
    service = QueryService(str(temp_project))
    assert service.query_rhythm()["rhythm_data"]["volume_1"]["pacing_label"] == "快节奏"

    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1], "beat_types": ["hook"],
            "emotion_intensity": [5], "pacing_score": 0.99,
        }
    })
    assert service.query_rhythm()["rhythm_data"]["volume_1"]["pacing_label"] == "快节奏"


def test_query_rhythm_pacing_label_medium(temp_project):
    """0.4 <= pacing_score < 0.7 → 中等节奏."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1], "beat_types": ["hook"],
            "emotion_intensity": [5], "pacing_score": 0.4,
        }
    })
    service = QueryService(str(temp_project))
    assert service.query_rhythm()["rhythm_data"]["volume_1"]["pacing_label"] == "中等节奏"

    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1], "beat_types": ["hook"],
            "emotion_intensity": [5], "pacing_score": 0.69,
        }
    })
    assert service.query_rhythm()["rhythm_data"]["volume_1"]["pacing_label"] == "中等节奏"


def test_query_rhythm_pacing_label_slow(temp_project):
    """pacing_score < 0.4 → 慢节奏."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1], "beat_types": ["hook"],
            "emotion_intensity": [5], "pacing_score": 0.39,
        }
    })
    service = QueryService(str(temp_project))
    assert service.query_rhythm()["rhythm_data"]["volume_1"]["pacing_label"] == "慢节奏"


# ---------------------------------------------------------------------------
# Test 7: Empty volume (no chapters) → graceful handling
# ---------------------------------------------------------------------------

def test_query_rhythm_empty_volume(temp_project):
    """章节列表为空 → avg_emotion_intensity=0, total_chapters=0."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [],
            "beat_types": [],
            "emotion_intensity": [],
            "pacing_score": 0.0,
        }
    })

    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    vol = result["rhythm_data"]["volume_1"]
    assert vol["total_chapters"] == 0
    assert vol["avg_emotion_intensity"] == 0.0
    assert vol["emotion_curve"] == []
    assert vol["climax_chapters"] == []
    assert vol["pacing_label"] == "慢节奏"


# ---------------------------------------------------------------------------
# Test 8: Unknown beat_types not in default distribution → ignored
# ---------------------------------------------------------------------------

def test_query_rhythm_unknown_beat_type_ignored(temp_project):
    """未知的 beat_type 不在 distribution 中 → 不报错."""
    write_rhythm(temp_project, {
        "volume_1": {
            "chapters": [1, 2],
            "beat_types": ["hook", "unknown_beat"],
            "emotion_intensity": [3, 5],
            "pacing_score": 0.5,
        }
    })

    service = QueryService(str(temp_project))
    result = service.query_rhythm()

    dist = result["rhythm_data"]["volume_1"]["beat_distribution"]
    assert dist["hook"] == 1
    assert "unknown_beat" not in dist
    assert dist["development"] == 0


# ---------------------------------------------------------------------------
# Tests for foreshadowing (Task 501) — preserved
# ---------------------------------------------------------------------------

from dashboard.query_service import QueryService as QS_orig

def write_state(project_root: Path, data: dict) -> None:
    state_path = project_root / ".webnovel" / "state.json"
    state_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_query_foreshadowing_happy_path(temp_project):
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
    service = QS_orig(str(temp_project))
    result = service.query_foreshadowing()
    assert result["stats"]["total"] == 5
    urgencies = [r["urgency"] for r in result["foreshadowing"]]
    assert urgencies == sorted(urgencies, reverse=True)
    assert result["stats"]["planted"] == 4
    assert result["stats"]["revealed"] == 1
    by_tier = result["by_tier"]
    assert len(by_tier["chapter"]) == 1
    assert len(by_tier["volume"]) == 3
    assert len(by_tier["book"]) == 1


def test_query_foreshadowing_no_state_file(temp_project):
    service = QS_orig(str(temp_project))
    result = service.query_foreshadowing()
    assert result["foreshadowing"] == []
    assert result["stats"]["total"] == 0


def test_query_foreshadowing_overdue_is_critical(temp_project):
    write_state(temp_project, {
        "last_written_chapter": 50,
        "foreshadowing": [
            {"id": "overdue1", "plant_chapter": 5, "reveal_chapter": 20, "status": "planted", "weight": 1.0},
            {"id": "overdue2", "plant_chapter": 1, "reveal_chapter": 10, "status": "planted", "weight": 0.5},
        ],
    })
    service = QS_orig(str(temp_project))
    result = service.query_foreshadowing()
    for r in result["foreshadowing"]:
        assert r["urgency"] == 1.0
        assert r["urgency_level"] == "critical"
    assert result["stats"]["overdue"] == 2


def test_query_foreshadowing_revealed_urgency_zero(temp_project):
    write_state(temp_project, {
        "last_written_chapter": 100,
        "foreshadowing": [
            {"id": "fs_a", "plant_chapter": 5, "reveal_chapter": 20, "status": "revealed", "weight": 2.0},
        ],
    })
    service = QS_orig(str(temp_project))
    result = service.query_foreshadowing()
    assert result["foreshadowing"][0]["urgency"] == 0.0
    assert result["stats"]["recovery_rate"] == 1.0


def test_query_foreshadowing_missing_optional_fields(temp_project):
    write_state(temp_project, {
        "last_written_chapter": 10,
        "foreshadowing": [{"id": "fs1"}],
    })
    service = QS_orig(str(temp_project))
    result = service.query_foreshadowing()
    fs = result["foreshadowing"][0]
    assert fs["plant_chapter"] == 0
    assert fs["reveal_chapter"] == 10
    assert fs["weight"] == 1.0
    assert fs["status"] == "planted"


def test_query_foreshadowing_chapters_remaining(temp_project):
    write_state(temp_project, {
        "last_written_chapter": 12,
        "foreshadowing": [
            {"id": "fs1", "plant_chapter": 5, "reveal_chapter": 20, "status": "planted"},
            {"id": "fs2", "plant_chapter": 5, "reveal_chapter": 10, "status": "planted"},
        ],
    })
    service = QS_orig(str(temp_project))
    result = service.query_foreshadowing()
    fs1 = next(r for r in result["foreshadowing"] if r["id"] == "fs1")
    assert fs1["chapters_remaining"] == 8
    fs2 = next(r for r in result["foreshadowing"] if r["id"] == "fs2")
    assert fs2["chapters_remaining"] == 0


# ---------------------------------------------------------------------------
# Tests for golden_finger (Task 503)
# ---------------------------------------------------------------------------

def write_golden_finger(project_root: Path, data: dict) -> None:
    """Helper to write golden_finger_tracker.json."""
    path = project_root / ".webnovel" / "golden_finger_tracker.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_query_golden_finger_no_file(temp_project):
    """golden_finger_tracker.json 不存在 → 返回 success=True, golden_finger 空结构."""
    service = QueryService(str(temp_project))
    result = service.query_golden_finger()
    assert result["success"] is True
    assert result["golden_finger"] is None


def test_query_golden_finger_happy_path(temp_project):
    """正常数据 → 解析 level/progress_percent/current_effects/cooldown_status/evolution_stages 正确."""
    write_golden_finger(temp_project, {
        "gf_id": "healing_system",
        "gf_name": "治愈系统",
        "gf_type": "system",
        "current_level": 3,
        "max_level": 10,
        "unlock_conditions": ["章节20解锁"],
        "activation_history": [
            {"chapter": 25, "level": 1, "effect": "治愈外伤"},
            {"chapter": 40, "level": 2, "effect": "治愈内伤"},
        ],
        "current_effects": ["治愈外伤", "治愈内伤", "解毒(新)"],
        "cooldown_chapters": 5,
        "recent_activations": [
            {"chapter": 45, "cooldown_remaining": 3},
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_golden_finger()

    assert result["success"] is True
    gf = result["golden_finger"]
    assert gf["id"] == "healing_system"
    assert gf["name"] == "治愈系统"
    assert gf["type"] == "system"
    assert gf["level"] == 3
    assert gf["max_level"] == 10
    # progress_percent = 3 / 10 * 100
    assert gf["progress_percent"] == 30.0
    assert gf["current_effects"] == ["治愈外伤", "治愈内伤", "解毒(新)"]
    assert gf["activation_count"] == 2
    # cooldown: remaining=3 > 0 → active=True, remaining_chapters=3
    assert gf["cooldown_status"]["active"] is True
    assert gf["cooldown_status"]["remaining_chapters"] == 3
    assert gf["cooldown_status"]["recent_chapter"] == 45
    # evolution_stages: [3, 6, 9] — level 节点
    assert gf["evolution_stages"] == [3, 6, 9]


def test_query_golden_finger_no_cooldown(temp_project):
    """cooldown_remaining == 0 → active=False."""
    write_golden_finger(temp_project, {
        "gf_id": "sword_system",
        "gf_name": "剑道系统",
        "current_level": 1,
        "max_level": 5,
        "current_effects": ["基础剑法"],
        "cooldown_chapters": 3,
        "recent_activations": [
            {"chapter": 10, "cooldown_remaining": 0},
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_golden_finger()

    assert result["golden_finger"]["cooldown_status"]["active"] is False
    assert result["golden_finger"]["cooldown_status"]["remaining_chapters"] == 0


def test_query_golden_finger_empty_recent_activations(temp_project):
    """recent_activations 为空 → cooldown_status 为 None 值."""
    write_golden_finger(temp_project, {
        "gf_id": "empty_gf",
        "gf_name": "空系统",
        "current_level": 1,
        "max_level": 5,
        "current_effects": [],
        "cooldown_chapters": 0,
        "recent_activations": [],
    })

    service = QueryService(str(temp_project))
    result = service.query_golden_finger()

    assert result["golden_finger"]["cooldown_status"]["active"] is False
    assert result["golden_finger"]["cooldown_status"]["remaining_chapters"] is None
    assert result["golden_finger"]["cooldown_status"]["recent_chapter"] is None
    assert result["golden_finger"]["activation_count"] == 0


# ---------------------------------------------------------------------------
# Tests for debt (Task 503)
# ---------------------------------------------------------------------------

def write_debt(project_root: Path, data: dict) -> None:
    """Helper to write debt_tracker.json."""
    path = project_root / ".webnovel" / "debt_tracker.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_query_debt_no_file(temp_project):
    """debt_tracker.json 不存在 → 返回空结构."""
    service = QueryService(str(temp_project))
    result = service.query_debt()
    assert result["success"] is True
    assert result["debt_summary"]["total_unresolved"] == 0
    assert result["debt_summary"]["total_resolved"] == 0


def test_query_debt_unresolved_only(temp_project):
    """只有未解决债务 → 统计正确."""
    write_debt(temp_project, {
        "unresolved_plot_debts": [
            {"id": "debt_001", "plant_chapter": 10, "foreshadowing_text": "神秘老者",
             "expected_payoff_chapter": 50, "weight": 3, "status": "unresolved"},
            {"id": "debt_002", "plant_chapter": 5, "foreshadowing_text": "宝剑",
             "expected_payoff_chapter": 30, "weight": 2, "status": "unresolved"},
        ],
        "resolved_plot_debts": [],
    })

    # 模拟当前章节 = 40（debt_001 尚未过期，debt_002 已过期）
    (temp_project / ".webnovel" / "state.json").write_text(
        json.dumps({"last_written_chapter": 40}), encoding="utf-8"
    )

    service = QueryService(str(temp_project))
    result = service.query_debt()

    summary = result["debt_summary"]
    assert summary["total_unresolved"] == 2
    assert summary["total_resolved"] == 0
    # debt_002: expected=30, current=40 → overdue=10
    # debt_001: expected=50, current=40 → 未过期
    assert summary["resolution_rate"] == 0.0
    # critical_debts: weight >= 4 且 unresolved → none
    assert summary["critical_debts"] == []


def test_query_debt_critical_debts(temp_project):
    """weight >= 4 的 unresolved 债务 → critical_debts."""
    write_debt(temp_project, {
        "unresolved_plot_debts": [
            {"id": "critical_1", "plant_chapter": 5, "foreshadowing_text": "主线",
             "expected_payoff_chapter": 20, "weight": 4, "status": "unresolved"},
            {"id": "critical_2", "plant_chapter": 3, "foreshadowing_text": "核心",
             "expected_payoff_chapter": 15, "weight": 5, "status": "unresolved"},
            {"id": "normal_1", "plant_chapter": 10, "foreshadowing_text": "支线",
             "expected_payoff_chapter": 50, "weight": 2, "status": "unresolved"},
        ],
        "resolved_plot_debts": [],
    })

    (temp_project / ".webnovel" / "state.json").write_text(
        json.dumps({"last_written_chapter": 30}), encoding="utf-8"
    )

    service = QueryService(str(temp_project))
    result = service.query_debt()

    critical = result["debt_summary"]["critical_debts"]
    assert len(critical) == 2
    ids = {c["id"] for c in critical}
    assert ids == {"critical_1", "critical_2"}
    # critical_1: overdue = 30 - 20 = 10
    c1 = next(c for c in critical if c["id"] == "critical_1")
    assert c1["overdue_chapters"] == 10
    assert c1["plant_chapter"] == 5
    assert c1["expected_payoff_chapter"] == 20
    # critical_2: overdue = 30 - 15 = 15
    c2 = next(c for c in critical if c["id"] == "critical_2")
    assert c2["overdue_chapters"] == 15


def test_query_debt_resolution_rate(temp_project):
    """resolution_rate = resolved / total * 100."""
    write_debt(temp_project, {
        "unresolved_plot_debts": [
            {"id": "un1", "plant_chapter": 1, "foreshadowing_text": "未解决",
             "expected_payoff_chapter": 10, "weight": 1, "status": "unresolved"},
        ],
        "resolved_plot_debts": [
            {"id": "res1", "plant_chapter": 5, "payoff_chapter": 30,
             "foreshadowing_text": "已解决1", "resolution_quality": 4, "status": "resolved"},
            {"id": "res2", "plant_chapter": 3, "payoff_chapter": 25,
             "foreshadowing_text": "已解决2", "resolution_quality": 3, "status": "resolved"},
            {"id": "res3", "plant_chapter": 8, "payoff_chapter": 40,
             "foreshadowing_text": "已解决3", "resolution_quality": 5, "status": "resolved"},
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_debt()

    summary = result["debt_summary"]
    assert summary["total_unresolved"] == 1
    assert summary["total_resolved"] == 3
    assert summary["resolution_rate"] == 75.0


def test_query_debt_recently_resolved(temp_project):
    """recently_resolved 最多返回 5 个，按 payoff_chapter 降序（最近的在前）."""
    write_debt(temp_project, {
        "unresolved_plot_debts": [],
        "resolved_plot_debts": [
            {"id": f"res{i}", "plant_chapter": i * 5, "payoff_chapter": i * 10,
             "foreshadowing_text": f"已解决{i}", "resolution_quality": i % 5 + 1, "status": "resolved"}
            for i in range(1, 8)
        ],
    })

    service = QueryService(str(temp_project))
    result = service.query_debt()

    recent = result["debt_summary"]["recently_resolved"]
    assert len(recent) == 5
    # 按 payoff_chapter 降序
    assert [r["id"] for r in recent] == ["res7", "res6", "res5", "res4", "res3"]


def test_query_debt_no_overdue(temp_project):
    """所有债务未到期 → overdue_chapters = 0."""
    write_debt(temp_project, {
        "unresolved_plot_debts": [
            {"id": "future_1", "plant_chapter": 10, "foreshadowing_text": "未来",
             "expected_payoff_chapter": 100, "weight": 4, "status": "unresolved"},
        ],
        "resolved_plot_debts": [],
    })

    (temp_project / ".webnovel" / "state.json").write_text(
        json.dumps({"last_written_chapter": 50}), encoding="utf-8"
    )

    service = QueryService(str(temp_project))
    result = service.query_debt()

    critical = result["debt_summary"]["critical_debts"]
    assert critical[0]["overdue_chapters"] == 0
    assert critical[0]["urgency"] == 4.0  # weight * 1.0 (not overdue, factor=1)
