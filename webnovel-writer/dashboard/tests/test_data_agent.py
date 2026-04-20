"""Tests for DataAgent."""
from __future__ import annotations

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from dashboard.skill_handlers.data_agent import DataAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project root."""
    return tmp_path


@pytest.fixture
def basic_context(temp_project):
    """Minimal context for DataAgent.run()."""
    return {
        "project_root": str(temp_project),
        "chapter_num": 1,
        "polished_text": "第一章正文。这是一个测试章节的内容。\n\n第二段内容。",
    }


@pytest.fixture
def context_with_all_texts(temp_project):
    """Context with all possible text sources."""
    return {
        "project_root": str(temp_project),
        "chapter_num": 2,
        "draft_text": "草稿文本",
        "adapted_text": "适配文本",
        "polished_text": "润色文本",
        "user_final_text": "用户最终文本",
    }


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

class TestDataAgentRunHappyPath:
    """Happy path: DataAgent.run() completes full pipeline."""

    @pytest.mark.asyncio
    async def test_run_saves_chapter_file(self, basic_context, temp_project):
        """Step 5 saves chapter text to 正本/第N章.md."""
        agent = DataAgent(basic_context)
        result = await agent.run()

        chapter_path = temp_project / "正文" / "第1章.md"
        assert chapter_path.exists()
        assert chapter_path.read_text(encoding="utf-8") == basic_context["polished_text"]
        assert result["results"]["chapter_saved"] == str(chapter_path)

    @pytest.mark.asyncio
    async def test_run_extracts_entities(self, basic_context, temp_project):
        """Step 5 calls extract_entities on chapter."""
        agent = DataAgent(basic_context)
        with patch.object(agent.adapter, "extract_entities", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "success": True,
                "entities": [
                    {"name": "张三", "type": "character", "attributes": {"身份": "主角"}},
                ],
            }
            result = await agent.run()

            mock_extract.assert_called_once()
            assert result["results"]["entities_extracted"] == 1

    @pytest.mark.asyncio
    async def test_run_generates_summary(self, basic_context, temp_project):
        """Step 5 calls generate_summary on chapter."""
        agent = DataAgent(basic_context)
        with patch.object(agent.adapter, "generate_summary", new_callable=AsyncMock) as mock_summary:
            mock_summary.return_value = {
                "success": True,
                "summary": "这是章节摘要。",
                "key_events": [],
            }
            result = await agent.run()

            mock_summary.assert_called_once()
            assert result["results"]["summary_generated"] is True

            summary_path = temp_project / ".webnovel" / "summaries" / "chapter_1.txt"
            assert summary_path.exists()
            assert summary_path.read_text(encoding="utf-8") == "这是章节摘要。"

    @pytest.mark.asyncio
    async def test_run_slices_scenes(self, basic_context, temp_project):
        """Step 5 creates scene slices for RAG."""
        agent = DataAgent(basic_context)
        result = await agent.run()

        scenes_path = temp_project / ".webnovel" / "scenes" / "chapter_1.json"
        assert scenes_path.exists()
        scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
        assert len(scenes) >= 1
        assert all("chapter" in s and "scene_index" in s and "text" in s for s in scenes)

    @pytest.mark.asyncio
    async def test_run_updates_state(self, basic_context, temp_project):
        """Step 5 updates state.json with chapter info."""
        agent = DataAgent(basic_context)
        result = await agent.run()

        state_path = temp_project / ".webnovel" / "state.json"
        assert state_path.exists()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert "1" in state["chapters"]
        assert state["chapters"]["1"]["status"] == "written"
        assert state["last_written_chapter"] == 1
        assert state["total_words"] > 0

    @pytest.mark.asyncio
    async def test_run_extracts_style_sample(self, basic_context, temp_project):
        """Step 5 saves style sample (first 500 chars)."""
        agent = DataAgent(basic_context)
        result = await agent.run()

        sample_path = temp_project / ".webnovel" / "style_samples" / "chapter_1.txt"
        assert sample_path.exists()
        assert len(sample_path.read_text(encoding="utf-8")) <= 500

    @pytest.mark.asyncio
    async def test_run_detects_debts(self, basic_context, temp_project):
        """Step 5 detects overdue foreshadowing debts."""
        # Pre-populate state with a planted foreshadowing that is overdue
        state_path = temp_project / ".webnovel" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "foreshadowing": [
                {
                    "id": "fs1",
                    "description": "神秘宝剑",
                    "status": "planted",
                    "plant_chapter": 1,
                    "reveal_chapter": 1,  # Should have been revealed in chapter 1
                }
            ]
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")

        agent = DataAgent(basic_context)
        result = await agent.run()

        assert result["results"]["debts_detected"] == 1
        debts = result["results"].get("debts", [])

    @pytest.mark.asyncio
    async def test_run_returns_results_and_instruction(self, basic_context):
        """DataAgent.run() returns structured results + instruction."""
        agent = DataAgent(basic_context)
        result = await agent.run()

        assert "results" in result
        assert "instruction" in result
        assert "entities_extracted" in result["results"]
        assert "summary_generated" in result["results"]
        assert "chapter_saved" in result["results"]

    @pytest.mark.asyncio
    async def test_run_prioritizes_user_final_text(self, context_with_all_texts, temp_project):
        """user_final_text takes priority over polished_text etc."""
        agent = DataAgent(context_with_all_texts)
        result = await agent.run()

        chapter_path = temp_project / "正文" / "第2章.md"
        content = chapter_path.read_text(encoding="utf-8")
        assert content == "用户最终文本"

    @pytest.mark.asyncio
    async def test_run_context_updated_with_final_text_and_chapter_path(self, basic_context):
        """DataAgent.run() mutates context with final_text and chapter_path."""
        agent = DataAgent(basic_context)
        await agent.run()

        assert "final_text" in basic_context
        assert "chapter_path" in basic_context
        assert basic_context["final_text"] == basic_context["polished_text"]


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestDataAgentEdgeCases:
    """Edge case 1: extract_entities returns empty list — no crash, no file writes."""

    @pytest.mark.asyncio
    async def test_empty_entities_does_not_write_settings(self, basic_context, temp_project):
        """Edge case: empty entities list → no setting files created."""
        agent = DataAgent(basic_context)
        with patch.object(agent.adapter, "extract_entities", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"success": True, "entities": []}
            result = await agent.run()

            assert result["results"]["entities_extracted"] == 0
            setting_dir = temp_project / "设定集"
            # No files should be created if no entities
            assert not setting_dir.exists() or not any(setting_dir.iterdir())

    @pytest.mark.asyncio
    async def test_empty_summary_does_not_write_summary_file(self, basic_context, temp_project):
        """Edge case: empty summary → no summary file written."""
        agent = DataAgent(basic_context)
        with patch.object(agent.adapter, "generate_summary", new_callable=AsyncMock) as mock_summary:
            mock_summary.return_value = {"success": True, "summary": ""}
            result = await agent.run()

            assert result["results"]["summary_generated"] is False
            summary_path = temp_project / ".webnovel" / "summaries" / "chapter_1.txt"
            assert not summary_path.exists()

    @pytest.mark.asyncio
    async def test_missing_polished_text_uses_draft(self, temp_project):
        """Edge case: no polished_text → falls back to draft_text."""
        context = {
            "project_root": str(temp_project),
            "chapter_num": 1,
            "draft_text": "草稿内容",
        }
        agent = DataAgent(context)
        result = await agent.run()

        chapter_path = temp_project / "正文" / "第1章.md"
        assert chapter_path.read_text(encoding="utf-8") == "草稿内容"

    @pytest.mark.asyncio
    async def test_no_debts_when_foreshadowing_absent(self, basic_context, temp_project):
        """Edge case: no foreshadowing in state → 0 debts."""
        agent = DataAgent(basic_context)
        result = await agent.run()

        assert result["results"]["debts_detected"] == 0

    @pytest.mark.asyncio
    async def test_no_debts_when_foreshadowing_resolved(self, basic_context, temp_project):
        """Edge case: foreshadowing marked resolved → not a debt."""
        state_path = temp_project / ".webnovel" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "foresearching": [],
            "foreshadowing": [
                {
                    "id": "fs1",
                    "description": "神秘宝剑",
                    "status": "resolved",  # Not "planted"
                    "reveal_chapter": 1,
                }
            ],
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")

        agent = DataAgent(basic_context)
        result = await agent.run()

        assert result["results"]["debts_detected"] == 0

    @pytest.mark.asyncio
    async def test_no_debts_when_foreshadowing_not_yet_due(self, basic_context, temp_project):
        """Edge case: foreshadowing reveal_chapter > current chapter → not yet due."""
        state_path = temp_project / ".webnovel" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "foreshadowing": [
                {
                    "id": "fs1",
                    "description": "神秘宝剑",
                    "status": "planted",
                    "plant_chapter": 1,
                    "reveal_chapter": 10,  # Future chapter
                }
            ],
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")

        agent = DataAgent(basic_context)
        result = await agent.run()

        assert result["results"]["debts_detected"] == 0


# ---------------------------------------------------------------------------
# Error case tests
# ---------------------------------------------------------------------------

class TestDataAgentErrorCases:
    """Error case: ScriptAdapter calls fail — graceful degradation."""

    @pytest.mark.asyncio
    async def test_extract_entities_error_does_not_crash(self, basic_context):
        """Error case: extract_entities throws → continues pipeline."""
        agent = DataAgent(basic_context)
        with patch.object(agent.adapter, "extract_entities", new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("Script error")
            result = await agent.run()

            # Should not crash, entities result is 0
            assert result["results"]["entities_extracted"] == 0
            # Chapter should still be saved
            assert result["results"]["chapter_saved"] is not None

    @pytest.mark.asyncio
    async def test_generate_summary_error_does_not_crash(self, basic_context):
        """Error case: generate_summary throws → continues pipeline."""
        agent = DataAgent(basic_context)
        with patch.object(agent.adapter, "generate_summary", new_callable=AsyncMock) as mock_summary:
            mock_summary.side_effect = Exception("Script error")
            result = await agent.run()

            assert result["results"]["summary_generated"] is False
            # Pipeline continues
            assert result["results"]["state_updated"] is True

    @pytest.mark.asyncio
    async def test_corrupt_state_json_skipped(self, basic_context, temp_project):
        """Error case: corrupt state.json → starts fresh state."""
        state_path = temp_project / ".webnovel" / "state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text("{ not valid json", encoding="utf-8")

        agent = DataAgent(basic_context)
        result = await agent.run()

        # Should not crash, state is reinitialized
        state = json.loads(state_path.read_text(encoding="utf-8"))
        assert "chapters" in state


# ---------------------------------------------------------------------------
# Helper method tests
# ---------------------------------------------------------------------------

class TestWriteEntitiesToSettings:
    """Tests for _write_entities_to_settings."""

    @pytest.mark.asyncio
    async def test_writes_character_to_main_roles_file(self, temp_project):
        """character type entity → 主要角色.md."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        entities = [{"name": "张三", "type": "character", "attributes": {"身份": "侠客"}}]
        await agent._write_entities_to_settings(entities)

        filepath = temp_project / "设定集" / "主要角色.md"
        assert filepath.exists()
        assert "张三" in filepath.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_writes_location_to_world_file(self, temp_project):
        """location type entity → 世界观.md."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        entities = [{"name": "青云山", "type": "location", "attributes": {"描述": "修仙圣地"}}]
        await agent._write_entities_to_settings(entities)

        filepath = temp_project / "设定集" / "世界观.md"
        assert filepath.exists()
        assert "青云山" in filepath.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_writes_power_to_power_file(self, temp_project):
        """power type entity → 力量体系.md."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        entities = [{"name": "剑气", "type": "power", "attributes": {"等级": "上品"}}]
        await agent._write_entities_to_settings(entities)

        filepath = temp_project / "设定集" / "力量体系.md"
        assert filepath.exists()
        assert "剑气" in filepath.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_writes_item_to_items_file(self, temp_project):
        """item type entity → 重要物品.md."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        entities = [{"name": "倚天剑", "type": "item", "attributes": {}}]
        await agent._write_entities_to_settings(entities)

        filepath = temp_project / "设定集" / "重要物品.md"
        assert filepath.exists()
        assert "倚天剑" in filepath.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_unknown_type_goes_to_other_file(self, temp_project):
        """Unknown type → 其他设定.md."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        entities = [{"name": "神秘", "type": "unknown_type", "attributes": {}}]
        await agent._write_entities_to_settings(entities)

        filepath = temp_project / "设定集" / "其他设定.md"
        assert filepath.exists()
        assert "神秘" in filepath.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_duplicate_entity_not_added_twice(self, temp_project):
        """If entity name already in file, skip duplicate."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})

        # First write
        await agent._write_entities_to_settings([{"name": "张三", "type": "character", "attributes": {}}])

        # Second write with same entity
        await agent._write_entities_to_settings([{"name": "张三", "type": "character", "attributes": {}}])

        filepath = temp_project / "设定集" / "主要角色.md"
        content = filepath.read_text(encoding="utf-8")
        # Should only appear once
        assert content.count("### 张三") == 1


class TestExtractStyleSample:
    """Tests for _extract_style_sample."""

    @pytest.mark.asyncio
    async def test_saves_first_500_chars(self, temp_project):
        """Style sample is capped at 500 characters."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        chapter_path = temp_project / "正文" / "第1章.md"
        chapter_path.parent.mkdir(parents=True, exist_ok=True)
        chapter_path.write_text("A" * 1000, encoding="utf-8")

        await agent._extract_style_sample(str(chapter_path))

        sample_path = temp_project / ".webnovel" / "style_samples" / "chapter_1.txt"
        assert len(sample_path.read_text(encoding="utf-8")) == 500

    @pytest.mark.asyncio
    async def test_keeps_only_last_3_samples(self, temp_project):
        """Only the 3 most recent style samples are kept."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        chapter_path = temp_project / "正文" / "第1章.md"
        chapter_path.parent.mkdir(parents=True, exist_ok=True)

        # Create 5 chapters
        for i in range(1, 6):
            agent.chapter_num = i
            chapter_path.write_text(f"Chapter {i} content" * 100, encoding="utf-8")
            await agent._extract_style_sample(str(chapter_path))

        samples = sorted((temp_project / ".webnovel" / "style_samples").glob("chapter_*.txt"))
        assert len(samples) == 3
        # Should be chapters 3, 4, 5 (last 3)
        sample_nums = [int(s.stem.split("_")[1]) for s in samples]
        assert sample_nums == [3, 4, 5]


class TestSliceScenes:
    """Tests for _slice_scenes."""

    @pytest.mark.asyncio
    async def test_scenes_grouped_by_3_paragraphs(self, temp_project):
        """Scenes are created from groups of 3 paragraphs."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        chapter_path = temp_project / "正文" / "第1章.md"
        chapter_path.parent.mkdir(parents=True, exist_ok=True)
        # 7 paragraphs → 3 scenes (3+3+1)
        chapter_path.write_text("p1\n\np2\n\np3\n\np4\n\np5\n\np6\n\np7", encoding="utf-8")

        scenes = await agent._slice_scenes(str(chapter_path))

        assert len(scenes) == 3
        assert scenes[0]["text"] == "p1\n\np2\n\np3"
        assert scenes[1]["text"] == "p4\n\np5\n\np6"
        assert scenes[2]["text"] == "p7"
        assert all(s["chapter"] == 1 for s in scenes)

    @pytest.mark.asyncio
    async def test_empty_chapter_returns_single_scene(self, temp_project):
        """Empty chapter still creates one scene."""
        agent = DataAgent({"project_root": str(temp_project), "chapter_num": 1})
        chapter_path = temp_project / "正文" / "第1章.md"
        chapter_path.parent.mkdir(parents=True, exist_ok=True)
        chapter_path.write_text("", encoding="utf-8")

        scenes = await agent._slice_scenes(str(chapter_path))

        assert len(scenes) == 0
