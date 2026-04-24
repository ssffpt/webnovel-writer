"""Tests for ContextBuilder — TDD for Task 303.

Tests:
- Happy path: extract_chapter_context success → rag_mode="full" → task_brief has 7 sections
- Edge case 1: extract_chapter_context fails → degraded mode → load_file_context used
- Edge case 2: idea_bank.json missing → core_constraints without creativity package, no error
- Error case: project_root doesn't exist → all sections return empty, no exception raised
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import sys

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.skill_handlers.context_builder import ContextBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_project(tmp_path: Path, with_idea_bank: bool = True) -> Path:
    """Create a minimal fake project structure."""
    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)

    outline_dir = tmp_path / "大纲"
    outline_dir.mkdir(parents=True, exist_ok=True)
    (outline_dir / "总纲.md").write_text("这是总纲", encoding="utf-8")

    setting_dir = tmp_path / "设定集"
    setting_dir.mkdir(parents=True, exist_ok=True)
    (setting_dir / "世界观.md").write_text(
        "- 世界观设定：仙侠世界观\n- 主角不可修仙\n- 禁止使用现代武器", encoding="utf-8"
    )

    summary_dir = webnovel_dir / "summaries"
    summary_dir.mkdir(parents=True, exist_ok=True)
    (summary_dir / "ch0001.md").write_text(
        "## 剧情摘要\n这是第1章摘要", encoding="utf-8"
    )

    if with_idea_bank:
        idea_bank = {
            "creativity_package": {
                "constraints": [
                    {"type": "tone", "content": "语气需古典雅致"},
                    {"type": "pacing", "content": "每章至少3个冲突点"},
                ]
            }
        }
        (webnovel_dir / "idea_bank.json").write_text(
            json.dumps(idea_bank, ensure_ascii=False), encoding="utf-8"
        )

    state_data = {"current_timeline": "第1章结尾：主角刚获得金手指"}
    (webnovel_dir / "state.json").write_text(
        json.dumps(state_data, ensure_ascii=False), encoding="utf-8"
    )

    # Style samples
    style_dir = webnovel_dir / "style_samples"
    style_dir.mkdir(parents=True, exist_ok=True)
    (style_dir / "sample1.txt").write_text("文笔风格样本一", encoding="utf-8")
    (style_dir / "sample2.txt").write_text("文笔风格样本二", encoding="utf-8")

    return tmp_path


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_happy_path_rag_mode_full():
    """extract_chapter_context succeeds → rag_mode='full' → task_brief has 7 sections."""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=True)

    fake_payload = {
        "success": True,
        "chapter": 2,
        "outline": "第2章：大綱",
        "previous_summaries": ["第1章摘要内容"],
        "state_summary": "当前状态",
        "settings": "- 仙侠世界观\n- 主角不可修仙",
        "foreshadowing": ["伏笔A", "伏笔B"],
        "character_states": {"主角": {"power": "level 1"}},
        "constraints": "核心约束1\n核心约束2",
        "context_contract_version": "v1",
        "context_weight_stage": "stage1",
        "reader_signal": {},
        "genre_profile": {},
        "writing_guidance": {},
        "rag_assist": {"invoked": True},
    }

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return fake_payload

    async def fake_load_file_context(chapter_num, context_window=5):
        # Should not be called in happy path
        return {"success": True, "fallback": True}

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 2,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context

    result = await builder.build()

    assert result["rag_mode"] == "full"
    assert result["instruction"] == "上下文构建完成（完整模式）"

    task_brief = result["task_brief"]
    assert "chapter_outline" in task_brief
    assert "previous_summaries" in task_brief
    assert "relevant_settings" in task_brief
    assert "pending_foreshadowing" in task_brief
    assert "character_states" in task_brief
    assert "core_constraints" in task_brief
    assert "style_reference" in task_brief

    # All 7 sections present
    assert len(task_brief) == 7

    # core_constraints includes creativity package from idea_bank.json
    assert "创意约束包" in task_brief["core_constraints"]
    assert "语气需古典雅致" in task_brief["core_constraints"]
    assert "每章至少3个冲突点" in task_brief["core_constraints"]

    # style_reference loaded from style_samples
    assert "文笔风格样本一" in task_brief["style_reference"]
    assert "文笔风格样本二" in task_brief["style_reference"]

    # context_contract has 4 sections
    contract = result["context_contract"]
    assert "setting_constraints" in contract
    assert "foreshadowing_obligations" in contract
    assert "timeline_anchor" in contract
    assert "character_boundaries" in contract

    # timeline_anchor from state.json
    assert "第1章结尾" in contract["timeline_anchor"]

    # execution_pack
    ep = context["execution_pack"]
    assert ep["chapter_num"] == 2
    assert ep["word_target"]["min"] == 2000
    assert ep["word_target"]["max"] == 2500
    assert ep["mode"] == "standard"


# ---------------------------------------------------------------------------
# Edge case 1: RAG degraded mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_rag_degraded_mode():
    """extract_chapter_context fails → degraded mode → load_file_context used."""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {"success": False, "error": "RAG unavailable", "fallback": True}

    async def fake_load_file_context(chapter_num, context_window=5):
        return {
            "success": True,
            "fallback": True,
            "outline": "来自文件系统的章节大纲",
            "previous_summaries": ["文件系统摘要1", "文件系统摘要2"],
            "settings": "文件系统设定",
            "foreshadowing": ["伏笔C"],
            "character_states": {"配角": {"power": "level 5"}},
            "constraints": "文件系统约束",
        }

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 3,
        "mode": "fast",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context

    result = await builder.build()

    assert result["rag_mode"] == "degraded"
    assert "降级模式" in result["instruction"]

    task_brief = result["task_brief"]
    assert task_brief["chapter_outline"] == "来自文件系统的章节大纲"
    assert "文件系统摘要1" in task_brief["previous_summaries"]

    contract = result["context_contract"]
    assert contract["foreshadowing_obligations"] == ["伏笔C"]
    assert contract["character_boundaries"] == {"配角": {"power": "level 5"}}


# ---------------------------------------------------------------------------
# Edge case 2: idea_bank.json missing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_no_idea_bank_no_error():
    """idea_bank.json missing → core_constraints without creativity package, no error."""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {
            "success": True,
            "outline": "章节大纲",
            "previous_summaries": [],
            "settings": "设定文本",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "基础约束",
        }

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 1,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context

    result = await builder.build()

    assert result["rag_mode"] == "full"
    # No creativity package section
    assert "创意约束包" not in result["task_brief"]["core_constraints"]
    # Base constraints still present
    assert "基础约束" in result["task_brief"]["core_constraints"]


# ---------------------------------------------------------------------------
# Error case: project_root doesn't exist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_build_nonexistent_project_root_no_exception():
    """Nonexistent project_root → all sections return empty, no exception."""
    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {"success": False, "error": "project missing", "fallback": True}

    async def fake_load_file_context(chapter_num, context_window=5):
        return {
            "success": True,
            "fallback": True,
            "outline": "",
            "previous_summaries": [],
            "settings": "",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }

    context = {
        "project_root": "/nonexistent/root/path",
        "chapter_num": 1,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context

    result = await builder.build()

    assert result["rag_mode"] == "degraded"
    task_brief = result["task_brief"]
    assert task_brief["chapter_outline"] == ""
    assert task_brief["previous_summaries"] == []
    assert task_brief["relevant_settings"] == ""
    assert task_brief["pending_foreshadowing"] == []
    assert task_brief["character_states"] == {}
    assert task_brief["core_constraints"] == ""
    assert task_brief["style_reference"] == ""

    contract = result["context_contract"]
    assert contract["setting_constraints"] == []
    assert contract["foreshadowing_obligations"] == []
    assert contract["timeline_anchor"] == ""
    assert contract["character_boundaries"] == {}


# ---------------------------------------------------------------------------
# Tests: _extract_setting_constraints helper
# ---------------------------------------------------------------------------

def test_extract_setting_constraints():
    """_extract_setting_constraints extracts hard constraints from settings text."""
    builder = ContextBuilder({})
    settings = (
        "- 这是一条普通设定\n"
        "- 主角不可修仙\n"
        "- 禁止使用现代武器\n"
        "- 必须遵守门派规矩\n"
        "这是普通描述文本"
    )
    result = builder._extract_setting_constraints({"settings": settings})
    assert "主角不可修仙" in result
    assert "禁止使用现代武器" in result
    assert "必须遵守门派规矩" in result
    assert "普通设定" not in result
    assert "普通描述文本" not in result


# ---------------------------------------------------------------------------
# Tests: _load_core_constraints with bad idea_bank.json
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_load_core_constraints_malformed_idea_bank_no_error():
    """Malformed idea_bank.json → silently ignored, no exception."""
    tmp_path = Path(tempfile.mkdtemp())
    webnovel_dir = tmp_path / ".webnovel"
    webnovel_dir.mkdir(parents=True, exist_ok=True)
    (webnovel_dir / "idea_bank.json").write_text("not valid json{{{", encoding="utf-8")

    builder = ContextBuilder({"project_root": str(tmp_path), "chapter_num": 1})
    result = builder._load_core_constraints({"constraints": "base"})

    assert "base" in result
    assert "创意约束包" not in result


# ---------------------------------------------------------------------------
# Tests: execute_step integration (write_handler step_1)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_handler_step_1_integration():
    """WriteSkillHandler.execute_step(step_1) uses ContextBuilder and returns expected fields."""
    from dashboard.skill_handlers.write_handler import WriteSkillHandler
    from dashboard.skill_models import StepState

    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {
            "success": True,
            "outline": "测试大纲",
            "previous_summaries": [],
            "settings": "测试设定",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "测试约束",
        }

    # Patch at module level
    with patch(
        "dashboard.skill_handlers.context_builder.ScriptAdapter"
    ) as MockAdapter:
        mock_instance = MockAdapter.return_value
        mock_instance.extract_chapter_context = fake_extract_chapter_context
        mock_instance.load_file_context = AsyncMock(
            return_value={
                "success": True,
                "fallback": True,
                "outline": "",
                "previous_summaries": [],
                "settings": "",
                "foreshadowing": [],
                "character_states": {},
                "constraints": "",
            }
        )

        handler = WriteSkillHandler()
        step = StepState(step_id="step_1", status="running")
        context = {"project_root": str(tmp_path), "chapter_num": 1, "mode": "standard"}
        result = await handler.execute_step(step, context)

    assert "task_brief" in result
    assert "context_contract" in result
    assert "rag_mode" in result
    assert "instruction" in result


# ---------------------------------------------------------------------------
# Task 604: Context Agent RAG 模式集成
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_rag_mode_with_rag_available():
    """RAG 可用时，extract 失败 → rag_mode='rag' → settings 包含 [RAG] 标记。"""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    # 为 _build_rag_queries 提供大纲文件
    vol_dir = tmp_path / "大纲" / "第1卷"
    vol_dir.mkdir(parents=True, exist_ok=True)
    (vol_dir / "第2章.md").write_text("主角获得金手指，开始修炼", encoding="utf-8")

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {"success": False, "error": "script unavailable", "fallback": True}

    async def fake_load_file_context(chapter_num, context_window=5):
        return {
            "success": True,
            "fallback": True,
            "outline": "章节大纲",
            "previous_summaries": ["摘要1"],
            "settings": "基础设定",
            "foreshadowing": ["伏笔A"],
            "character_states": {},
            "constraints": "",
        }

    async def fake_rag_search(query, top_k=10):
        return {
            "success": True,
            "results": [
                {"text": "RAG检索到的设定片段", "source": "设定.md", "score": 0.9, "metadata": {}},
            ],
            "error": None,
        }

    def fake_rag_is_available():
        return True

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 2,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context
    builder.adapter.rag_search = fake_rag_search
    builder.adapter.rag_is_available = fake_rag_is_available

    result = await builder.build()

    assert result["rag_mode"] == "rag"
    assert "RAG 增强模式" in result["instruction"]
    # settings 应包含 [RAG] 标记
    assert "[RAG]" in result["task_brief"]["relevant_settings"]


@pytest.mark.asyncio
async def test_build_rag_not_available_degraded():
    """RAG 不可用时 → rag_mode='degraded'。"""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {"success": False, "error": "script unavailable", "fallback": True}

    async def fake_load_file_context(chapter_num, context_window=5):
        return {
            "success": True,
            "fallback": True,
            "outline": "",
            "previous_summaries": [],
            "settings": "",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }

    def fake_rag_is_available():
        return False

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 1,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context
    builder.adapter.rag_is_available = fake_rag_is_available

    result = await builder.build()

    assert result["rag_mode"] == "degraded"
    assert "降级模式" in result["instruction"]


@pytest.mark.asyncio
async def test_build_rag_search_empty_results():
    """RAG 检索返回空结果 → 合并后数据与降级模式相同，不报错。"""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {"success": False, "fallback": True}

    async def fake_load_file_context(chapter_num, context_window=5):
        return {
            "success": True,
            "fallback": True,
            "outline": "章节大纲",
            "previous_summaries": ["摘要1"],
            "settings": "基础设定",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }

    async def fake_rag_search(query, top_k=10):
        return {"success": True, "results": [], "error": None}

    def fake_rag_is_available():
        return True

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 1,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context
    builder.adapter.rag_search = fake_rag_search
    builder.adapter.rag_is_available = fake_rag_is_available

    result = await builder.build()

    assert result["rag_mode"] == "rag"
    # 无 [RAG] 标记（因为空结果）
    assert "[RAG]" not in result["task_brief"]["relevant_settings"]


@pytest.mark.asyncio
async def test_build_rag_search_failure_uses_base_data():
    """rag_search 失败 → 跳过该维度，使用基础数据。"""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    # 提供大纲文件让 _build_rag_queries 有内容
    vol_dir = tmp_path / "大纲" / "第1卷"
    vol_dir.mkdir(parents=True, exist_ok=True)
    (vol_dir / "第1章.md").write_text("主角修炼", encoding="utf-8")

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {"success": False, "fallback": True}

    async def fake_load_file_context(chapter_num, context_window=5):
        return {
            "success": True,
            "fallback": True,
            "outline": "章节大纲",
            "previous_summaries": ["摘要1"],
            "settings": "基础设定",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }

    async def fake_rag_search(query, top_k=10):
        return {"success": False, "results": [], "error": "API error"}

    def fake_rag_is_available():
        return True

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 1,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context
    builder.adapter.load_file_context = fake_load_file_context
    builder.adapter.rag_search = fake_rag_search
    builder.adapter.rag_is_available = fake_rag_is_available

    result = await builder.build()

    assert result["rag_mode"] == "rag"
    # 基础数据仍在
    assert result["task_brief"]["chapter_outline"] == "章节大纲"


@pytest.mark.asyncio
async def test_build_full_mode_no_rag_needed():
    """extract_chapter_context 成功 → rag_mode='full' → 不走 RAG 路径。"""
    tmp_path = Path(tempfile.mkdtemp())
    make_fake_project(tmp_path, with_idea_bank=False)

    async def fake_extract_chapter_context(chapter_num, context_window=5):
        return {
            "success": True,
            "outline": "完整大纲",
            "previous_summaries": [],
            "settings": "完整设定",
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }

    context = {
        "project_root": str(tmp_path),
        "chapter_num": 1,
        "mode": "standard",
    }
    builder = ContextBuilder(context)
    builder.adapter.extract_chapter_context = fake_extract_chapter_context

    result = await builder.build()

    assert result["rag_mode"] == "full"
    assert "完整模式" in result["instruction"]
