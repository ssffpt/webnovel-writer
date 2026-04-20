"""Tests for rag_config.py — TDD for Task 601."""
from __future__ import annotations

import json
import os
import pytest
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.rag_config import RAGConfig


# ---------------------------------------------------------------------------
# Helper: tmpdir fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def tmpdir():
    """Create a temp dir and chdir to it. Returns Path."""
    d = tempfile.mkdtemp()
    orig = os.getcwd()
    os.chdir(d)
    yield Path(d)
    os.chdir(orig)


# ---------------------------------------------------------------------------
# Happy path: get/set basic operations
# ---------------------------------------------------------------------------

def test_get_returns_none_when_no_files(tmpdir):
    """get() 在无配置文件时返回 None 或 default。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get("ANY_KEY") is None


def test_set_creates_config_json(tmpdir):
    """set() 创建 rag_config.json 并写入键值。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("RAG_EMBEDDING_MODEL", "text-embedding-3-large")
    assert tmpdir.joinpath(".webnovel/rag_config.json").is_file()
    data = json.loads(tmpdir.joinpath(".webnovel/rag_config.json").read_text())
    assert data["RAG_EMBEDDING_MODEL"] == "text-embedding-3-large"


def test_set_multiple_keys(tmpdir):
    """set() 可以多次调用累积写入。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("key1", "value1")
    config.set("key2", "value2")
    data = json.loads(tmpdir.joinpath(".webnovel/rag_config.json").read_text())
    assert data["key1"] == "value1"
    assert data["key2"] == "value2"


def test_get_reads_from_config_json(tmpdir):
    """get() 能从 rag_config.json 读取。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("CHUNK_SIZE", "1000")
    # 新建另一个 RAGConfig 实例（模拟读取）
    config2 = RAGConfig(project_root=str(tmpdir))
    assert config2.get("CHUNK_SIZE") == "1000"


# ---------------------------------------------------------------------------
# Edge case 1: get_openai_key from .env
# ---------------------------------------------------------------------------

def test_get_openai_key_from_env(tmpdir):
    """get_openai_key() 从 .env 读取。"""
    env_file = tmpdir / ".env"
    env_file.write_text('OPENAI_API_KEY=sk-test-12345\nRAG_ENABLED=true\n')
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_openai_key() == "sk-test-12345"


def test_get_openai_key_quoted_value(tmpdir):
    """get_openai_key() 处理带引号的 .env 值。"""
    env_file = tmpdir / ".env"
    env_file.write_text('OPENAI_API_KEY="sk-quoted-abc"\n')
    config = RAGConfig(project_root=str(tmpdir))
    # 读取时去掉引号
    assert config.get_openai_key() == "sk-quoted-abc"


def test_get_openai_key_single_quoted(tmpdir):
    """get_openai_key() 处理单引号包裹的 .env 值。"""
    env_file = tmpdir / ".env"
    env_file.write_text("OPENAI_API_KEY='sk-single-789'\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_openai_key() == "sk-single-789"


def test_get_openai_key_not_found_returns_none(tmpdir):
    """get_openai_key() 在 .env 中不存在时返回 None。"""
    env_file = tmpdir / ".env"
    env_file.write_text("OTHER_KEY=value\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_openai_key() is None


# ---------------------------------------------------------------------------
# Edge case 2: get_embedding_model default value
# ---------------------------------------------------------------------------

def test_get_embedding_model_default(tmpdir):
    """get_embedding_model() 默认值为 text-embedding-3-small。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_embedding_model() == "text-embedding-3-small"


def test_get_embedding_model_from_env(tmpdir):
    """get_embedding_model() 优先从 .env 读取。"""
    env_file = tmpdir / ".env"
    env_file.write_text("RAG_EMBEDDING_MODEL=text-embedding-ada-002\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_embedding_model() == "text-embedding-ada-002"


def test_get_embedding_model_from_config_json(tmpdir):
    """get_embedding_model() 从 rag_config.json 读取（优先级低于 .env）。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("RAG_EMBEDDING_MODEL", "text-embedding-3-large")
    config2 = RAGConfig(project_root=str(tmpdir))
    assert config2.get_embedding_model() == "text-embedding-3-large"


# ---------------------------------------------------------------------------
# Edge case 3: is_rag_enabled() — default false, set to true
# ---------------------------------------------------------------------------

def test_is_rag_enabled_default_false(tmpdir):
    """is_rag_enabled() 默认返回 False。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.is_rag_enabled() is False


def test_is_rag_enabled_true_from_env(tmpdir):
    """is_rag_enabled() 从 .env 读取 RAG_ENABLED=true。"""
    env_file = tmpdir / ".env"
    env_file.write_text("RAG_ENABLED=true\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.is_rag_enabled() is True


def test_is_rag_enabled_true_from_config_json(tmpdir):
    """is_rag_enabled() 从 rag_config.json 读取。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("RAG_ENABLED", "true")
    config2 = RAGConfig(project_root=str(tmpdir))
    assert config2.is_rag_enabled() is True


def test_is_rag_enabled_false_explicit(tmpdir):
    """is_rag_enabled() 返回 False（非 true 字符串）。"""
    env_file = tmpdir / ".env"
    env_file.write_text("RAG_ENABLED=false\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.is_rag_enabled() is False


# ---------------------------------------------------------------------------
# Edge case 4: config.json auto-created when .webnovel doesn't exist
# ---------------------------------------------------------------------------

def test_config_json_auto_created_when_webnovel_missing(tmpdir):
    """set() 在 .webnovel 不存在时自动创建目录和文件。"""
    assert not tmpdir.joinpath(".webnovel").exists()
    config = RAGConfig(project_root=str(tmpdir))
    config.set("NEW_KEY", "NEW_VALUE")
    assert tmpdir.joinpath(".webnovel").is_dir()
    assert tmpdir.joinpath(".webnovel/rag_config.json").is_file()


def test_config_json_not_overwritten_by_read(tmpdir):
    """读取操作不修改 rag_config.json。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("SAVED_KEY", "SAVED_VALUE")
    # 读取（不写入）
    config2 = RAGConfig(project_root=str(tmpdir))
    result = config2.get("SAVED_KEY")
    assert result == "SAVED_VALUE"


# ---------------------------------------------------------------------------
# Edge case 5: .env priority over config.json
# ---------------------------------------------------------------------------

def test_env_priority_over_config_json(tmpdir):
    """get() 优先从 .env 读取，而非 rag_config.json。"""
    # 在 config.json 中设置
    config = RAGConfig(project_root=str(tmpdir))
    config.set("RAG_EMBEDDING_MODEL", "model-from-json")
    # 在 .env 中设置不同值
    env_file = tmpdir / ".env"
    env_file.write_text("RAG_EMBEDDING_MODEL=model-from-env\n")
    # 重新读取，应该取 .env 的值
    config2 = RAGConfig(project_root=str(tmpdir))
    assert config2.get_embedding_model() == "model-from-env"


def test_env_key_missing_in_config_json(tmpdir):
    """某个 key 在 .env 中有、config.json 中没有，优先取 .env。"""
    env_file = tmpdir / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-env\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_openai_key() == "sk-from-env"


# ---------------------------------------------------------------------------
# Error case: corrupted config.json is handled gracefully
# ---------------------------------------------------------------------------

def test_corrupted_config_json_fallback_to_default(tmpdir):
    """config.json 内容损坏时 get() 返回 default，不抛出异常。"""
    webnovel_dir = tmpdir / ".webnovel"
    webnovel_dir.mkdir()
    (webnovel_dir / "rag_config.json").write_text("{ invalid json }")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get("ANY_KEY", "default_val") == "default_val"


def test_corrupted_config_json_get_embedding_model(tmpdir):
    """config.json 损坏时 get_embedding_model() 使用默认值。"""
    webnovel_dir = tmpdir / ".webnovel"
    webnovel_dir.mkdir()
    (webnovel_dir / "rag_config.json").write_text("{ broken")
    config = RAGConfig(project_root=str(tmpdir))
    # 使用 .env 中的值或默认值
    assert config.get_embedding_model() == "text-embedding-3-small"


def test_env_file_with_malformed_lines(tmpdir):
    """.env 有格式不规范的行（如无等号）时不影响解析。"""
    env_file = tmpdir / ".env"
    env_file.write_text("MALFORMED_LINE\nOPENAI_API_KEY=sk-valid\n# comment\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_openai_key() == "sk-valid"


# ---------------------------------------------------------------------------
# Edge case: get_chunk_size / get_chunk_overlap
# ---------------------------------------------------------------------------

def test_get_chunk_size_default(tmpdir):
    """get_chunk_size() 默认值为 500。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_chunk_size() == 500


def test_get_chunk_size_from_env(tmpdir):
    """get_chunk_size() 从 .env 读取并转为 int。"""
    env_file = tmpdir / ".env"
    env_file.write_text("RAG_CHUNK_SIZE=1000\n")
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_chunk_size() == 1000


def test_get_chunk_overlap_default(tmpdir):
    """get_chunk_overlap() 默认值为 50。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get_chunk_overlap() == 50


def test_get_chunk_overlap_from_config_json(tmpdir):
    """get_chunk_overlap() 从 config.json 读取。"""
    config = RAGConfig(project_root=str(tmpdir))
    config.set("RAG_CHUNK_OVERLAP", "100")
    config2 = RAGConfig(project_root=str(tmpdir))
    assert config2.get_chunk_overlap() == 100


def test_get_with_default(tmpdir):
    """get() 支持传入 default 参数。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get("MISSING", "fallback") == "fallback"


def test_get_none_for_missing_key_no_default(tmpdir):
    """get() 无 default 时对缺失 key 返回 None。"""
    config = RAGConfig(project_root=str(tmpdir))
    assert config.get("MISSING") is None


# ---------------------------------------------------------------------------
# Task 603: 索引构建任务管理
# ---------------------------------------------------------------------------

import pytest


@pytest.mark.asyncio
async def test_start_build_index_starts_task(tmpdir):
    """start_build_index 返回 task_id 和 status=started。"""
    config = RAGConfig(project_root=str(tmpdir))
    # 清空之前的任务（类级别状态）
    RAGConfig._build_tasks.clear()

    result = await config.start_build_index()

    assert result["task_id"] is not None
    assert result["status"] == "started"

    # 清理
    RAGConfig._build_tasks.clear()


@pytest.mark.asyncio
async def test_start_build_index_already_running(tmpdir):
    """重复启动返回 already_running。"""
    RAGConfig._build_tasks.clear()
    config = RAGConfig(project_root=str(tmpdir))

    # 模拟一个正在运行的任务
    RAGConfig._build_tasks["fake_id"] = {
        "status": "running",
        "progress": 0.5,
        "message": "building",
        "started_at": "2026-01-01T00:00:00",
        "completed_at": None,
        "result": None,
    }

    result = await config.start_build_index()

    assert result["status"] == "already_running"
    assert result["task_id"] is None

    RAGConfig._build_tasks.clear()


@pytest.mark.asyncio
async def test_get_build_status_no_tasks(tmpdir):
    """无构建任务时返回 none 状态。"""
    RAGConfig._build_tasks.clear()
    config = RAGConfig(project_root=str(tmpdir))

    result = config.get_build_status()

    assert result["status"] == "none"
    assert result["task_id"] is None


@pytest.mark.asyncio
async def test_get_build_status_specific_task(tmpdir):
    """查询指定 task_id 的状态。"""
    RAGConfig._build_tasks.clear()
    config = RAGConfig(project_root=str(tmpdir))

    RAGConfig._build_tasks["abc123"] = {
        "status": "completed",
        "progress": 1.0,
        "message": "done",
        "started_at": "2026-01-01T00:00:00",
        "completed_at": "2026-01-01T00:01:00",
        "result": {"doc_count": 5},
    }

    result = config.get_build_status("abc123")

    assert result["task_id"] == "abc123"
    assert result["status"] == "completed"
    assert result["result"]["doc_count"] == 5

    RAGConfig._build_tasks.clear()


@pytest.mark.asyncio
async def test_get_build_status_latest_task(tmpdir):
    """不指定 task_id 时返回最近的任务。"""
    RAGConfig._build_tasks.clear()
    config = RAGConfig(project_root=str(tmpdir))

    RAGConfig._build_tasks["old_task"] = {
        "status": "completed",
        "progress": 1.0,
        "message": "old",
        "started_at": "2026-01-01T00:00:00",
        "completed_at": "2026-01-01T00:01:00",
        "result": None,
    }
    RAGConfig._build_tasks["new_task"] = {
        "status": "running",
        "progress": 0.5,
        "message": "current",
        "started_at": "2026-01-02T00:00:00",
        "completed_at": None,
        "result": None,
    }

    result = config.get_build_status()

    assert result["task_id"] == "new_task"
    assert result["status"] == "running"

    RAGConfig._build_tasks.clear()


@pytest.mark.asyncio
async def test_start_build_index_sse_callback(tmpdir):
    """start_build_index 在 on_progress 时调用 sse_callback。"""
    RAGConfig._build_tasks.clear()
    config = RAGConfig(project_root=str(tmpdir))

    sse_events = []

    def sse_callback(event_data):
        sse_events.append(event_data)

    # 启动（没有章节文件，构建会很快完成）
    result = await config.start_build_index(sse_callback=sse_callback)

    assert result["status"] == "started"

    # 等待后台任务完成
    import asyncio
    for _ in range(50):
        status = config.get_build_status(result["task_id"])
        if status["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.1)

    # 应该收到 build_completed 事件
    event_types = [e.get("type") for e in sse_events]
    assert "rag.build_completed" in event_types

    RAGConfig._build_tasks.clear()