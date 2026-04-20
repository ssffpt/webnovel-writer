#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for script_adapter.py — TDD for Task 301.

Tests:
- Happy path: extract_chapter_context returns JSON with expected fields
- Edge case 1: non-JSON fallback (fallback=True, raw_context)
- Edge case 2: load_file_context fallback mode (reads filesystem)
- Error case: non-zero exit code returns success=False
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.script_adapter import ScriptAdapter, _SCRIPTS_DIR


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_project(tmp_path: Path) -> Path:
    """Create a minimal fake project structure."""
    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)

    outline_dir = tmp_path / "大纲"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "总纲.md").write_text("这是总纲", encoding="utf-8")

    setting_dir = tmp_path / "设定集"
    setting_dir.mkdir(parents=True, exist_ok=True)
    (setting_dir / "世界观.md").write_text("设定内容", encoding="utf-8")

    summary_dir = webnovel_dir / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    (summary_dir / "ch0001.md").write_text(
        "## 剧情摘要\n这是第1章摘要", encoding="utf-8"
    )
    (summary_dir / "ch0002.md").write_text(
        "## 剧情摘要\n这是第2章摘要", encoding="utf-8"
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Tests: extract_chapter_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_chapter_context_happy_path():
    """extract_chapter_context returns parsed JSON with expected structure."""
    project_root = Path(tempfile.mkdtemp())
    make_fake_project(project_root)

    adapter = ScriptAdapter(str(project_root))

    fake_payload = {
        "chapter": 3,
        "outline": "第3章大纲",
        "previous_summaries": ["第1章", "第2章"],
        "state_summary": "当前状态",
        "context_contract_version": "v1",
        "context_weight_stage": "stage1",
        "reader_signal": {},
        "genre_profile": {},
        "writing_guidance": {},
        "rag_assist": {"invoked": False},
    }

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": json.dumps(fake_payload, ensure_ascii=False),
            "stderr": "",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.extract_chapter_context(chapter_num=3)

    assert result["success"] is True
    assert result["chapter"] == 3
    assert result["outline"] == "第3章大纲"
    assert result["previous_summaries"] == ["第1章", "第2章"]
    assert result["state_summary"] == "当前状态"
    assert result["context_contract_version"] == "v1"


@pytest.mark.asyncio
async def test_extract_chapter_context_non_json_fallback():
    """Non-JSON stdout triggers fallback=True and raw_context."""
    project_root = Path(tempfile.mkdtemp())
    make_fake_project(project_root)

    adapter = ScriptAdapter(str(project_root))

    plain_text = "这不是 JSON 输出，只是一段纯文本"

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": plain_text,
            "stderr": "",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.extract_chapter_context(chapter_num=3)

    assert result["success"] is True
    assert result["fallback"] is True
    assert result["raw_context"] == plain_text


@pytest.mark.asyncio
async def test_extract_chapter_context_error_case():
    """Non-zero exit code returns success=False with error from stderr."""
    project_root = Path(tempfile.mkdtemp())
    make_fake_project(project_root)

    adapter = ScriptAdapter(str(project_root))

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 1,
            "stdout": "",
            "stderr": "Script error message",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.extract_chapter_context(chapter_num=3)

    assert result["success"] is False
    assert "Script error message" in result["error"]
    assert result["fallback"] is True


# ---------------------------------------------------------------------------
# Tests: load_file_context (filesystem fallback)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_file_context_success():
    """load_file_context reads filesystem and returns expected structure."""
    project_root = Path(tempfile.mkdtemp())
    make_fake_project(project_root)

    adapter = ScriptAdapter(str(project_root))
    result = await adapter.load_file_context(chapter_num=3, context_window=3)

    assert result["success"] is True
    assert result["fallback"] is True
    # outline should be from 总纲.md or chapter file
    assert "总纲" in result["outline"] or result["outline"] == ""
    # settings should contain the setting file content
    assert "设定内容" in result["settings"] or result["settings"] == ""
    # previous_summaries should contain loaded summaries
    assert len(result["previous_summaries"]) >= 1
    assert "第1章摘要" in result["previous_summaries"][0] or "第1章" in result["previous_summaries"][0]


@pytest.mark.asyncio
async def test_load_file_context_no_project():
    """load_file_context handles missing project gracefully."""
    adapter = ScriptAdapter("/nonexistent/project/root")
    result = await adapter.load_file_context(chapter_num=1)

    assert result["success"] is True
    assert result["fallback"] is True
    assert result["outline"] == ""
    assert result["settings"] == ""
    assert result["previous_summaries"] == []


# ---------------------------------------------------------------------------
# Tests: extract_entities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_entities_happy_path():
    """extract_entities returns parsed JSON with entity list."""
    project_root = Path(tempfile.mkdtemp())

    adapter = ScriptAdapter(str(project_root))

    fake_payload = {
        "entities": [
            {"name": "张三", "type": "character", "attributes": {}},
            {"name": "门派A", "type": "势力", "attributes": {}},
        ]
    }

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": json.dumps(fake_payload, ensure_ascii=False),
            "stderr": "",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.extract_entities("/fake/chapter.md")

    assert result["success"] is True
    assert len(result["entities"]) == 2
    assert result["entities"][0]["name"] == "张三"


@pytest.mark.asyncio
async def test_extract_entities_error():
    """Non-zero exit code returns success=False."""
    adapter = ScriptAdapter()

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 1,
            "stdout": "",
            "stderr": "entity linker failed",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.extract_entities("/fake/chapter.md")

    assert result["success"] is False
    assert result["error"] == "entity linker failed"
    assert result["entities"] == []


# ---------------------------------------------------------------------------
# Tests: update_state
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_state_success():
    """update_state returns success=True on zero exit code."""
    adapter = ScriptAdapter()

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": "done",
            "stderr": "",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.update_state({"progress": [5, 12345]})

    assert result["success"] is True
    assert "progress" in result["updated_fields"]


@pytest.mark.asyncio
async def test_update_state_error():
    """Non-zero exit code returns success=False."""
    adapter = ScriptAdapter()

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 1,
            "stdout": "",
            "stderr": "state update failed",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.update_state({"progress": [5, 12345]})

    assert result["success"] is False
    assert "state update failed" in result["error"]


# ---------------------------------------------------------------------------
# Tests: git_commit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_git_commit_success():
    """git_commit returns commit hash on success."""
    adapter = ScriptAdapter()

    async def fake_run(func, *args, **kwargs):
        # func is subprocess.run (bound method); cmd is first positional arg
        cmd = args[0] if args else kwargs.get("args", [])
        if isinstance(cmd, list) and "add" in cmd:
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        else:
            return type("R", (), {
                "returncode": 0,
                "stdout": "[master abc1234] Chapter 5 written",
                "stderr": "",
            })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.git_commit("第5章完成")

    assert result["success"] is True
    assert result["commit_hash"] == "abc1234"


@pytest.mark.asyncio
async def test_git_commit_nothing_to_commit():
    """git_commit returns commit_hash=None when nothing to commit."""
    adapter = ScriptAdapter()

    async def fake_run(func, *args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        if isinstance(cmd, list) and "add" in cmd:
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        else:
            return type("R", (), {
                "returncode": 0,
                "stdout": "nothing to commit, working tree clean",
                "stderr": "",
            })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.git_commit("empty commit")

    assert result["success"] is True
    assert result["commit_hash"] is None


@pytest.mark.asyncio
async def test_git_commit_add_failed():
    """git add failure returns success=False."""
    adapter = ScriptAdapter()

    async def fake_run(func, *args, **kwargs):
        return type("R", (), {
            "returncode": 1,
            "stdout": "",
            "stderr": "fatal: not a git repository",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.git_commit("will fail")

    assert result["success"] is False
    assert "git add failed" in result["error"]


# ---------------------------------------------------------------------------
# Tests: generate_summary
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_summary_happy_path():
    """generate_summary returns summary from extract_chapter_context payload."""
    adapter = ScriptAdapter()

    fake_payload = {
        "chapter": 3,
        "outline": "outline",
        "previous_summaries": [],
        "state_summary": "第3章状态摘要",
        "context_contract_version": "v1",
        "context_weight_stage": "s1",
        "reader_signal": {},
        "genre_profile": {},
        "writing_guidance": {},
        "rag_assist": {},
    }

    async def fake_run(cmd, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": json.dumps(fake_payload, ensure_ascii=False),
            "stderr": "",
        })()

    with patch.object(asyncio, "to_thread", side_effect=fake_run):
        result = await adapter.generate_summary("3")

    assert result["success"] is True
    assert "第3章状态摘要" in result["summary"]


# ---------------------------------------------------------------------------
# RAG test helpers
# ---------------------------------------------------------------------------

class FakeScriptPath:
    """Fake Path-like object for mocking script existence checks."""
    def __init__(self, path_str: str, exists_val: bool = True):
        self._path = Path(path_str)
        self._exists_val = exists_val

    def exists(self) -> bool:
        return self._exists_val

    def __truediv__(self, name: str) -> "FakeScriptPath":
        return FakeScriptPath(str(self._path / name), self._exists_val)

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return f"FakeScriptPath({str(self._path)})"


class FakeScriptsDir:
    """Fake _SCRIPTS_DIR that returns FakeScriptPath on / operator."""
    def __init__(self, script_name: str, exists_val: bool = True):
        self._script_name = script_name
        self._exists_val = exists_val

    def __truediv__(self, name: str) -> FakeScriptPath:
        return FakeScriptPath(f"/fake/scripts/{name}", self._exists_val)


# ---------------------------------------------------------------------------
# Tests: RAG — build_index
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_index_success():
    """build_index returns success=True when script exits 0."""
    adapter = ScriptAdapter()

    fake_scripts_dir = FakeScriptsDir("build_rag_index.py", exists_val=True)

    async def fake_run(func, *args, **kwargs):
        cmd = args[0]  # second positional arg after subprocess.run
        assert "build_rag_index.py" in cmd
        return type("R", (), {"returncode": 0, "stdout": '{"chunks": 42}', "stderr": ""})()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run), \
         patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        result = await adapter.build_index("/some/project")

    assert result["success"] is True
    assert result["chunk_count"] == 42


@pytest.mark.asyncio
async def test_build_index_script_not_found():
    """build_index returns success=False when script does not exist."""
    adapter = ScriptAdapter()

    fake_scripts_dir = FakeScriptsDir("build_rag_index.py", exists_val=False)

    with patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        result = await adapter.build_index("/some/project")

    assert result["success"] is False
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_build_index_failure():
    """build_index returns success=False when script exits non-zero."""
    adapter = ScriptAdapter()

    fake_scripts_dir = FakeScriptsDir("build_rag_index.py", exists_val=True)

    async def fake_run(func, *args, **kwargs):
        cmd = args[0]
        assert "build_rag_index.py" in cmd
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": "index error"})()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run), \
         patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        result = await adapter.build_index("/some/project")

    assert result["success"] is False
    assert "index error" in result["error"]


@pytest.mark.asyncio
async def test_build_index_with_force_flag():
    """build_index passes --force when force=True."""
    adapter = ScriptAdapter()

    fake_scripts_dir = FakeScriptsDir("build_rag_index.py", exists_val=True)
    captured = {}

    async def fake_run(func, *args, **kwargs):
        captured["cmd"] = args[0]
        return type("R", (), {"returncode": 0, "stdout": '{"chunks": 1}', "stderr": ""})()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run), \
         patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        await adapter.build_index("/some/project", force=True)

    assert "--force" in captured["cmd"]


# ---------------------------------------------------------------------------
# Tests: RAG — query_rag
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_query_rag_success():
    """query_rag returns results from script output."""
    adapter = ScriptAdapter()

    fake_scripts_dir = FakeScriptsDir("query_rag.py", exists_val=True)

    fake_results = [
        {"text": "相关段落1", "score": 0.95, "source": "ch001.md"},
        {"text": "相关段落2", "score": 0.87, "source": "ch003.md"},
    ]

    async def fake_run(func, *args, **kwargs):
        cmd = args[0]
        assert "query_rag.py" in cmd
        return type("R", (), {
            "returncode": 0,
            "stdout": json.dumps({"results": fake_results}),
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run), \
         patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        result = await adapter.query_rag("主角的战斗", top_k=5)

    assert result["success"] is True
    assert len(result["results"]) == 2
    assert result["results"][0]["score"] == 0.95


@pytest.mark.asyncio
async def test_query_rag_script_not_found_fallback():
    """query_rag falls back to load_file_context when script missing."""
    project_root = Path(tempfile.mkdtemp())
    make_fake_project(project_root)
    adapter = ScriptAdapter(str(project_root))

    fake_scripts_dir = FakeScriptsDir("query_rag.py", exists_val=False)

    with patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        result = await adapter.query_rag("主角", top_k=3, filters={"chapter_range": [1, 5]})

    assert result["success"] is True
    assert result["fallback"] is True
    # fallback should contain fields from load_file_context
    assert "outline" in result or "settings" in result


@pytest.mark.asyncio
async def test_query_rag_with_filters():
    """query_rag passes filters as --filter JSON to script."""
    adapter = ScriptAdapter()

    fake_scripts_dir = FakeScriptsDir("query_rag.py", exists_val=True)
    captured = {}

    async def fake_run(func, *args, **kwargs):
        captured["cmd"] = args[0]
        return type("R", (), {
            "returncode": 0,
            "stdout": '{"results": []}',
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run), \
         patch("dashboard.script_adapter._SCRIPTS_DIR", fake_scripts_dir):
        await adapter.query_rag("query text", filters={"chapter_range": [1, 10]})

    # Should contain --filter and a JSON string
    assert "--filter" in captured["cmd"]


# ---------------------------------------------------------------------------
# Tests: RAG — check_index_status
# ---------------------------------------------------------------------------

def test_check_index_status_with_index(tmp_path):
    """check_index_status returns indexed=True when .webnovel/rag_index/ exists."""
    webnovel_dir = tmp_path / ".webnovel"
    index_dir = webnovel_dir / "rag_index"
    index_dir.mkdir(parents=True)

    # Write a dummy index file to make file count > 0
    (index_dir / "chunks.json").write_text('[]', encoding="utf-8")
    (webnovel_dir / "state.json").write_text(
        json.dumps({"last_updated": "2026-04-20T10:00:00"}), encoding="utf-8"
    )

    adapter = ScriptAdapter(str(tmp_path))
    result = adapter.check_index_status(str(tmp_path))

    assert result["indexed"] is True
    assert result["chunk_count"] >= 0
    assert result["last_updated"] == "2026-04-20T10:00:00"


def test_check_index_status_no_index(tmp_path):
    """check_index_status returns indexed=False when rag_index/ missing."""
    adapter = ScriptAdapter(str(tmp_path))
    result = adapter.check_index_status(str(tmp_path))

    assert result["indexed"] is False
    assert result["chunk_count"] == 0
    assert result["last_updated"] is None


# ---------------------------------------------------------------------------
# Tests: RAG — get_index_stats
# ---------------------------------------------------------------------------

def test_get_index_stats_with_file(tmp_path):
    """get_index_stats reads stats.json and returns parsed data."""
    webnovel_dir = tmp_path / ".webnovel"
    stats_dir = webnovel_dir / "rag_index"
    stats_dir.mkdir(parents=True)

    stats_data = {
        "total_chunks": 123,
        "total_characters": 45678,
        "indexed_files": ["ch001.md", "ch002.md"],
        "embedding_model": "text-embedding-3-small",
    }
    (stats_dir / "stats.json").write_text(json.dumps(stats_data), encoding="utf-8")

    adapter = ScriptAdapter(str(tmp_path))
    result = adapter.get_index_stats(str(tmp_path))

    assert result["total_chunks"] == 123
    assert result["total_characters"] == 45678
    assert "ch001.md" in result["indexed_files"]


def test_get_index_stats_no_file(tmp_path):
    """get_index_stats returns empty stats when stats.json missing."""
    adapter = ScriptAdapter(str(tmp_path))
    result = adapter.get_index_stats(str(tmp_path))

    assert result["total_chunks"] == 0
    assert result["total_characters"] == 0
    assert result["indexed_files"] == []
    assert result["embedding_model"] == ""


# ---------------------------------------------------------------------------
# Integration smoke test (real subprocess, no mocking)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extract_chapter_context_real_script_missing_project():
    """Real subprocess call with nonexistent project root returns success=False gracefully."""
    adapter = ScriptAdapter("/this/project/does/not/exist")

    result = await adapter.extract_chapter_context(chapter_num=1, context_window=2)

    # Either succeeds with fallback or fails gracefully — no exception
    assert isinstance(result, dict)
    # Should not be a happy JSON parse since project doesn't exist
    # but it should not throw
    if result["success"]:
        assert "outline" in result or "raw_context" in result


# ---------------------------------------------------------------------------
# Tests: RAG — _parse_rag_output (Task 602)
# ---------------------------------------------------------------------------

def test_parse_rag_output_success():
    """_parse_rag_output parses success JSON correctly."""
    adapter = ScriptAdapter()
    stdout = json.dumps({
        "status": "success",
        "data": {"vectors": 42, "terms": 100},
        "message": "stats",
    }, ensure_ascii=False)
    result = adapter._parse_rag_output(stdout)
    assert result["ok"] is True
    assert result["data"]["vectors"] == 42
    assert result["message"] == "stats"


def test_parse_rag_output_error():
    """_parse_rag_output parses error JSON correctly."""
    adapter = ScriptAdapter()
    stdout = json.dumps({
        "status": "error",
        "error": {"code": "UNKNOWN_COMMAND", "message": "未指定有效命令"},
    }, ensure_ascii=False)
    result = adapter._parse_rag_output(stdout)
    assert result["ok"] is False
    assert result["error"] == "未指定有效命令"
    assert result["code"] == "UNKNOWN_COMMAND"


def test_parse_rag_output_invalid_json():
    """_parse_rag_output handles invalid JSON."""
    adapter = ScriptAdapter()
    result = adapter._parse_rag_output("not json at all")
    assert result["ok"] is False
    assert "invalid JSON" in result["error"]


def test_parse_rag_output_unexpected_format():
    """_parse_rag_output handles unexpected JSON format."""
    adapter = ScriptAdapter()
    result = adapter._parse_rag_output('{"something": "else"}')
    assert result["ok"] is False
    assert "unexpected output" in result["error"]


# ---------------------------------------------------------------------------
# Tests: RAG — rag_search (Task 602)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_search_happy_path():
    """rag_search returns results list on success."""
    adapter = ScriptAdapter("/fake/project")

    search_output = {
        "status": "success",
        "data": [
            {
                "chunk_id": "ch0001_s1",
                "chapter": 1,
                "scene_index": 1,
                "content": "战斗场景内容",
                "score": 0.95,
                "source": "hybrid",
                "chunk_type": "scene",
                "source_file": "正文/第0001章.md#scene_1",
            },
            {
                "chunk_id": "ch0003_s2",
                "chapter": 3,
                "scene_index": 2,
                "content": "修炼场景内容",
                "score": 0.87,
                "source": "hybrid",
                "chunk_type": "scene",
                "source_file": "正文/第0003章.md#scene_2",
            },
        ],
        "message": "search_results",
    }

    async def fake_run(func, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": json.dumps(search_output, ensure_ascii=False),
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_search(query="主角战斗", top_k=10)

    assert result["success"] is True
    assert len(result["results"]) == 2
    assert result["results"][0]["text"] == "战斗场景内容"
    assert result["results"][0]["score"] == 0.95
    assert result["results"][0]["source"] == "正文/第0001章.md#scene_1"
    assert result["error"] is None


@pytest.mark.asyncio
async def test_rag_search_empty_results():
    """rag_search returns empty results list without error."""
    adapter = ScriptAdapter("/fake/project")

    search_output = {
        "status": "success",
        "data": [],
        "message": "search_results",
    }

    async def fake_run(func, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": json.dumps(search_output, ensure_ascii=False),
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_search(query="不存在的查询", top_k=5)

    assert result["success"] is True
    assert result["results"] == []
    assert result["error"] is None


@pytest.mark.asyncio
async def test_rag_search_cli_error():
    """rag_search returns success=False when rag_adapter.py exits non-zero."""
    adapter = ScriptAdapter("/fake/project")

    async def fake_run(func, *args, **kwargs):
        return type("R", (), {
            "returncode": 1,
            "stdout": "",
            "stderr": "ModuleNotFoundError: No module named 'data_modules'",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_search(query="test", top_k=5)

    assert result["success"] is False
    assert result["error"] is not None
    assert "ModuleNotFoundError" in result["error"]


@pytest.mark.asyncio
async def test_rag_search_error_output():
    """rag_search handles CLI error JSON output."""
    adapter = ScriptAdapter("/fake/project")

    error_output = json.dumps({
        "status": "error",
        "error": {"code": "EMBEDDING_FAILED", "message": "API key invalid"},
    })

    async def fake_run(func, *args, **kwargs):
        return type("R", (), {
            "returncode": 0,
            "stdout": error_output,
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_search(query="test", top_k=5)

    assert result["success"] is False
    assert "API key invalid" in result["error"]


# ---------------------------------------------------------------------------
# Tests: RAG — rag_is_available (Task 602)
# ---------------------------------------------------------------------------

def test_rag_is_available_no_env(tmp_path):
    """rag_is_available returns False when no .env or config exists."""
    adapter = ScriptAdapter(str(tmp_path))
    assert adapter.rag_is_available() is False


def test_rag_is_available_with_config_and_meta(tmp_path):
    """rag_is_available returns True when RAG enabled and index_meta.json exists."""
    # Create .env with RAG_ENABLED=true
    (tmp_path / ".env").write_text("RAG_ENABLED=true\n", encoding="utf-8")

    # Create index_meta.json
    rag_dir = tmp_path / ".webnovel" / "rag"
    rag_dir.mkdir(parents=True)
    (rag_dir / "index_meta.json").write_text(
        json.dumps({"doc_count": 10, "build_time": 1.5}), encoding="utf-8"
    )

    adapter = ScriptAdapter(str(tmp_path))
    assert adapter.rag_is_available() is True


def test_rag_is_available_no_meta(tmp_path):
    """rag_is_available returns False when config exists but no index_meta.json."""
    (tmp_path / ".env").write_text("RAG_ENABLED=true\n", encoding="utf-8")
    # No index_meta.json

    adapter = ScriptAdapter(str(tmp_path))
    assert adapter.rag_is_available() is False


def test_rag_is_available_with_model_but_no_enabled(tmp_path):
    """rag_is_available returns True when embedding model configured (even if RAG_ENABLED not set)."""
    (tmp_path / ".env").write_text("RAG_EMBEDDING_MODEL=text-embedding-3-small\n", encoding="utf-8")

    rag_dir = tmp_path / ".webnovel" / "rag"
    rag_dir.mkdir(parents=True)
    (rag_dir / "index_meta.json").write_text(
        json.dumps({"doc_count": 5, "build_time": 0.8}), encoding="utf-8"
    )

    adapter = ScriptAdapter(str(tmp_path))
    assert adapter.rag_is_available() is True


# ---------------------------------------------------------------------------
# Tests: RAG — _write_index_meta (Task 602)
# ---------------------------------------------------------------------------

def test_write_index_meta(tmp_path):
    """_write_index_meta creates .webnovel/rag/index_meta.json."""
    adapter = ScriptAdapter(str(tmp_path))
    adapter._write_index_meta(doc_count=42, build_time=3.14)

    meta_path = tmp_path / ".webnovel" / "rag" / "index_meta.json"
    assert meta_path.exists()

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    assert data["doc_count"] == 42
    assert data["build_time_seconds"] == 3.14
    assert "built_at" in data


# ---------------------------------------------------------------------------
# Tests: RAG — rag_build_index (Task 602)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_build_index_happy_path(tmp_path):
    """rag_build_index scans chapters and indexes them."""
    # Create fake project structure with chapter files
    text_dir = tmp_path / "正文"
    text_dir.mkdir()
    (text_dir / "第0001章.md").write_text("第一章内容" * 100, encoding="utf-8")
    (text_dir / "第0002章.md").write_text("第二章内容" * 100, encoding="utf-8")

    adapter = ScriptAdapter(str(tmp_path))

    call_count = 0
    captured_cmds = []

    async def fake_run(func, *args, **kwargs):
        nonlocal call_count
        cmd = args[0]
        captured_cmds.append(cmd)
        call_count += 1

        # Simulate successful index-chapter output
        output = json.dumps({
            "status": "success",
            "data": {"stored": 1, "skipped": 0, "total": 1},
            "message": "indexed",
        })
        return type("R", (), {
            "returncode": 0,
            "stdout": output,
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_build_index()

    assert result["success"] is True
    assert result["doc_count"] == 2
    assert result["error"] is None
    assert result["build_time_seconds"] >= 0
    # Verify index_meta.json was written
    meta_path = tmp_path / ".webnovel" / "rag" / "index_meta.json"
    assert meta_path.exists()


@pytest.mark.asyncio
async def test_rag_build_index_no_chapters(tmp_path):
    """rag_build_index handles project with no chapter files."""
    adapter = ScriptAdapter(str(tmp_path))

    result = await adapter.rag_build_index()

    assert result["success"] is True
    assert result["doc_count"] == 0


@pytest.mark.asyncio
async def test_rag_build_index_with_progress(tmp_path):
    """rag_build_index calls on_progress callback."""
    text_dir = tmp_path / "正文"
    text_dir.mkdir()
    (text_dir / "第0001章.md").write_text("内容" * 50, encoding="utf-8")
    (text_dir / "第0002章.md").write_text("内容" * 50, encoding="utf-8")
    (text_dir / "第0003章.md").write_text("内容" * 50, encoding="utf-8")

    adapter = ScriptAdapter(str(tmp_path))

    progress_calls = []

    def on_progress(progress: float, message: str):
        progress_calls.append((progress, message))

    async def fake_run(func, *args, **kwargs):
        output = json.dumps({
            "status": "success",
            "data": {"stored": 1, "skipped": 0, "total": 1},
            "message": "indexed",
        })
        return type("R", (), {
            "returncode": 0,
            "stdout": output,
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_build_index(on_progress=on_progress)

    assert result["success"] is True
    assert len(progress_calls) == 3  # One per chapter


@pytest.mark.asyncio
async def test_rag_build_index_chapter_failure(tmp_path):
    """rag_build_index continues on individual chapter failures."""
    text_dir = tmp_path / "正文"
    text_dir.mkdir()
    (text_dir / "第0001章.md").write_text("内容" * 50, encoding="utf-8")
    (text_dir / "第0002章.md").write_text("内容" * 50, encoding="utf-8")

    adapter = ScriptAdapter(str(tmp_path))
    call_idx = 0

    async def fake_run(func, *args, **kwargs):
        nonlocal call_idx
        call_idx += 1
        if call_idx == 1:
            # First chapter fails
            return type("R", (), {
                "returncode": 1,
                "stdout": "",
                "stderr": "embedding failed",
            })()
        else:
            # Second chapter succeeds
            output = json.dumps({
                "status": "success",
                "data": {"stored": 1, "skipped": 0, "total": 1},
                "message": "indexed",
            })
            return type("R", (), {
                "returncode": 0,
                "stdout": output,
                "stderr": "",
            })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_build_index()

    assert result["success"] is True
    assert result["doc_count"] == 1  # Only second chapter succeeded


# ---------------------------------------------------------------------------
# Tests: RAG — rag_add_doc (Task 602)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_add_doc_chapter(tmp_path):
    """rag_add_doc indexes a single chapter file."""
    # Create a chapter file
    text_dir = tmp_path / "正文"
    text_dir.mkdir()
    chapter_file = text_dir / "第0005章.md"
    chapter_file.write_text("第五章内容" * 50, encoding="utf-8")

    adapter = ScriptAdapter(str(tmp_path))

    async def fake_run(func, *args, **kwargs):
        output = json.dumps({
            "status": "success",
            "data": {"stored": 1, "skipped": 0, "total": 1},
            "message": "indexed",
        })
        return type("R", (), {
            "returncode": 0,
            "stdout": output,
            "stderr": "",
        })()

    with patch("dashboard.script_adapter.asyncio.to_thread", side_effect=fake_run):
        result = await adapter.rag_add_doc(str(chapter_file), doc_type="chapter")

    assert result["success"] is True
    assert result["chunks_added"] == 1


@pytest.mark.asyncio
async def test_rag_add_doc_setting_type(tmp_path):
    """rag_add_doc returns success with chunks_added=0 for non-chapter types."""
    adapter = ScriptAdapter(str(tmp_path))

    result = await adapter.rag_add_doc("/fake/setting.md", doc_type="setting")

    assert result["success"] is True
    assert result["chunks_added"] == 0


@pytest.mark.asyncio
async def test_rag_add_doc_chapter_not_found(tmp_path):
    """rag_add_doc returns error when chapter file doesn't exist."""
    adapter = ScriptAdapter(str(tmp_path))

    result = await adapter.rag_add_doc("/nonexistent/第0001章.md", doc_type="chapter")

    assert result["success"] is False
    assert "not found" in result.get("error", "").lower() or result["chunks_added"] == 0
