"""DataAgent — 章节写作后的数据处理流水线。"""

import json
from pathlib import Path
from ..script_adapter import ScriptAdapter


class DataAgent:
    def __init__(self, context: dict):
        self.context = context
        self.project_root = Path(context.get("project_root", "."))
        self.chapter_num = int(context.get("chapter_num", 1))
        self.adapter = ScriptAdapter(project_root=str(self.project_root))

    async def run(self) -> dict:
        """执行 Data Agent 全部流水线。"""
        results = {}

        # 1. 保存正文文件
        chapter_path = await self._save_chapter()
        results["chapter_saved"] = chapter_path

        # 2. 实体提取
        entities = await self._extract_entities(chapter_path)
        results["entities_extracted"] = len(entities)

        # 3. 生成摘要
        summary = await self._generate_summary(chapter_path)
        results["summary_generated"] = bool(summary)

        # 4. 场景切片（为 RAG 准备，Phase 6 完整实现）
        scenes = await self._slice_scenes(chapter_path)
        results["scenes_sliced"] = len(scenes)

        # 5. 更新 state.json
        await self._update_state(summary)
        results["state_updated"] = True

        # 6. 风格样本提取
        await self._extract_style_sample(chapter_path)
        results["style_sample_saved"] = True

        # 7. 债务检测（伏笔超期未回收）
        debts = await self._detect_debts()
        results["debts_detected"] = len(debts)

        self.context["data_agent_results"] = results

        return {
            "results": results,
            "instruction": f"数据处理完成：提取 {len(entities)} 个实体，生成摘要，检测 {len(debts)} 条债务",
        }

    async def _save_chapter(self) -> str:
        """保存正文到文件。"""
        final_text = (
            self.context.get("user_final_text")
            or self.context.get("polished_text")
            or self.context.get("adapted_text")
            or self.context.get("draft_text", "")
        )

        chapter_dir = self.project_root / "正文"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        chapter_path = chapter_dir / f"第{self.chapter_num}章.md"

        chapter_path.write_text(final_text, encoding="utf-8")
        self.context["final_text"] = final_text
        self.context["chapter_path"] = str(chapter_path)

        return str(chapter_path)

    async def _extract_entities(self, chapter_path: str) -> list[dict]:
        """调用 ScriptAdapter 提取实体。"""
        try:
            result = await self.adapter.extract_entities(chapter_path)
            entities = result.get("entities", [])
        except Exception:
            entities = []

        if entities:
            await self._write_entities_to_settings(entities)

        return entities

    async def _write_entities_to_settings(self, entities: list[dict]) -> None:
        """将新实体写入设定集文件。"""
        setting_dir = self.project_root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)

        by_type = {}
        for e in entities:
            etype = e.get("type", "其他")
            by_type.setdefault(etype, []).append(e)

        type_to_file = {
            "character": "主要角色.md",
            "location": "世界观.md",
            "power": "力量体系.md",
            "item": "重要物品.md",
        }

        for etype, elist in by_type.items():
            filename = type_to_file.get(etype, "其他设定.md")
            filepath = setting_dir / filename
            existing = filepath.read_text(encoding="utf-8") if filepath.exists() else f"# {filepath.stem}\n"

            additions = ""
            for e in elist:
                name = e.get("name", "")
                if name and name not in existing:
                    attrs = e.get("attributes", {})
                    attrs_str = "、".join(f"{k}: {v}" for k, v in attrs.items()) if attrs else ""
                    additions += f"\n### {name}\n\n{attrs_str}\n"

            if additions:
                filepath.write_text(existing + additions, encoding="utf-8")

    async def _generate_summary(self, chapter_path: str) -> str:
        """调用 ScriptAdapter 生成章节摘要。"""
        try:
            result = await self.adapter.generate_summary(chapter_path)
            summary = result.get("summary", "")
        except Exception:
            summary = ""

        if summary:
            summary_dir = self.project_root / ".webnovel" / "summaries"
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / f"chapter_{self.chapter_num}.txt"
            summary_path.write_text(summary, encoding="utf-8")

        return summary

    async def _slice_scenes(self, chapter_path: str) -> list[dict]:
        """场景切片（为 RAG 准备）。"""
        text = Path(chapter_path).read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        scenes = []
        current_scene = []
        for p in paragraphs:
            current_scene.append(p)
            if len(current_scene) >= 3:
                scenes.append({
                    "chapter": self.chapter_num,
                    "scene_index": len(scenes),
                    "text": "\n\n".join(current_scene),
                })
                current_scene = []

        if current_scene:
            scenes.append({
                "chapter": self.chapter_num,
                "scene_index": len(scenes),
                "text": "\n\n".join(current_scene),
            })

        scenes_dir = self.project_root / ".webnovel" / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)
        scenes_path = scenes_dir / f"chapter_{self.chapter_num}.json"
        scenes_path.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")

        return scenes

    async def _update_state(self, summary: str) -> None:
        """更新 state.json。"""
        state_path = self.project_root / ".webnovel" / "state.json"
        state = {}
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        if "chapters" not in state:
            state["chapters"] = {}
        state["chapters"][str(self.chapter_num)] = {
            "status": "written",
            "word_count": len(self.context.get("final_text", "")),
            "summary": summary[:100] if summary else "",
        }

        state["last_written_chapter"] = self.chapter_num
        state["total_words"] = sum(
            ch.get("word_count", 0) for ch in state.get("chapters", {}).values()
        )

        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    async def _extract_style_sample(self, chapter_path: str) -> None:
        """提取风格样本（保留最近 3 章的样本）。"""
        style_dir = self.project_root / ".webnovel" / "style_samples"
        style_dir.mkdir(parents=True, exist_ok=True)

        text = Path(chapter_path).read_text(encoding="utf-8")
        sample = text[:500]
        sample_path = style_dir / f"chapter_{self.chapter_num}.txt"
        sample_path.write_text(sample, encoding="utf-8")

        all_samples = sorted(style_dir.glob("chapter_*.txt"))
        for old in all_samples[:-3]:
            old.unlink()

    async def _detect_debts(self) -> list[dict]:
        """检测伏笔债务（超期未回收的伏笔）。"""
        state_path = self.project_root / ".webnovel" / "state.json"
        if not state_path.exists():
            return []

        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        foreshadowing = state.get("foreshadowing", [])
        debts = []
        for f in foreshadowing:
            if f.get("status") == "planted" and f.get("reveal_chapter"):
                if self.chapter_num >= f["reveal_chapter"]:
                    debts.append({
                        "id": f.get("id", ""),
                        "description": f.get("description", ""),
                        "planted_chapter": f.get("plant_chapter"),
                        "expected_reveal": f.get("reveal_chapter"),
                        "overdue_by": self.chapter_num - f["reveal_chapter"],
                    })

        return debts
