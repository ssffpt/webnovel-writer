# Task 307: Step 5 Data Agent + Step 6 Git 备份

## 目标

实现 WriteSkillHandler 的 Step 5（Data Agent：实体提取→摘要→状态更新）和 Step 6（Git 备份：可选自动提交）。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/write_handler.py`（修改 execute_step）
- `webnovel-writer/dashboard/skill_handlers/data_agent.py`（新建，Data Agent 逻辑）

## 依赖

- task-306（Step 4 完成后 context 包含 polished_text 或用户确认的最终文本）
- task-301（ScriptAdapter 的 extract_entities / generate_summary / update_state / git_commit 已实现）

## 前置知识

context 中已有的数据（来自 Step 4）：
- `context["polished_text"]` — 润色后文本（或用户手动修改的文本）
- `context["chapter_num"]` — 章节编号
- `context["project_root"]` — 项目根目录

Data Agent 的职责（按顺序）：
1. 保存正文文件
2. 实体提取 → 消歧 → 写入设定集
3. 生成章节摘要
4. 场景切片（为 RAG 准备）
5. 更新 state.json
6. 风格样本提取
7. 债务检测（伏笔超期未回收）

Git 备份（Step 6）：
- 默认关闭，通过 `.webnovel/config.json` 的 `auto_git_commit: true` 开启
- 提交信息格式：`[webnovel] 第{N}章 - {title}（write Step 6）`
- 失败不阻断流程

## 规格

### execute_step（Step 5 / Step 6）

```python
async def execute_step(self, step: StepState, context: dict) -> dict:
    if step.step_id == "step_5":
        from .data_agent import DataAgent
        agent = DataAgent(context)
        return await agent.run()
    if step.step_id == "step_6":
        return await self._git_backup(context)
    # ... 其他步骤
```

### data_agent.py

```python
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

        # 7. 债务检测
        debts = await self._detect_debts()
        results["debts_detected"] = len(debts)

        self.context["data_agent_results"] = results

        return {
            "results": results,
            "instruction": f"数据处理完成：提取 {len(entities)} 个实体，生成摘要，检测 {len(debts)} 条债务",
        }

    async def _save_chapter(self) -> str:
        """保存正文到文件。"""
        # 获取最终文本（优先用户修改 > polished > adapted > draft）
        final_text = (
            self.context.get("user_final_text")
            or self.context.get("polished_text")
            or self.context.get("adapted_text")
            or self.context.get("draft_text", "")
        )

        # 确定保存路径
        chapter_dir = self.project_root / "正文"
        chapter_dir.mkdir(parents=True, exist_ok=True)
        chapter_path = chapter_dir / f"第{self.chapter_num}章.md"

        chapter_path.write_text(final_text, encoding="utf-8")
        self.context["final_text"] = final_text
        self.context["chapter_path"] = str(chapter_path)

        return str(chapter_path)

    async def _extract_entities(self, chapter_path: str) -> list[dict]:
        """调用 ScriptAdapter 提取实体。"""
        result = await self.adapter.extract_entities(chapter_path)
        entities = result.get("entities", [])

        # 写入设定集（增量追加）
        if entities:
            await self._write_entities_to_settings(entities)

        return entities

    async def _write_entities_to_settings(self, entities: list[dict]) -> None:
        """将新实体写入设定集文件。"""
        setting_dir = self.project_root / "设定集"
        setting_dir.mkdir(parents=True, exist_ok=True)

        # 按类型分组
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
        result = await self.adapter.generate_summary(chapter_path)
        summary = result.get("summary", "")

        # 保存摘要
        if summary:
            summary_dir = self.project_root / ".webnovel" / "summaries"
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / f"chapter_{self.chapter_num}.txt"
            summary_path.write_text(summary, encoding="utf-8")

        return summary

    async def _slice_scenes(self, chapter_path: str) -> list[dict]:
        """场景切片（为 RAG 准备）。

        Phase 3 简化实现：按段落分割，每个场景 = 一个段落组。
        Phase 6 完整实现：语义切片 + 向量化。
        """
        text = Path(chapter_path).read_text(encoding="utf-8")
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        scenes = []
        current_scene = []
        for p in paragraphs:
            current_scene.append(p)
            # 简单规则：每 3 段或遇到场景切换标记为一个场景
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

        # 保存场景切片
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

        # 更新章节状态
        if "chapters" not in state:
            state["chapters"] = {}
        state["chapters"][str(self.chapter_num)] = {
            "status": "written",
            "word_count": len(self.context.get("final_text", "")),
            "summary": summary[:100] if summary else "",
        }

        # 更新总进度
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
        # 取前 500 字作为风格样本
        sample = text[:500]
        sample_path = style_dir / f"chapter_{self.chapter_num}.txt"
        sample_path.write_text(sample, encoding="utf-8")

        # 只保留最近 3 章的样本
        all_samples = sorted(style_dir.glob("chapter_*.txt"))
        for old in all_samples[:-3]:
            old.unlink()

    async def _detect_debts(self) -> list[dict]:
        """检测伏笔债务（超期未回收的伏笔）。

        简化实现：从 state.json 中读取伏笔列表，检查是否超期。
        """
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
                if self.chapter_num > f["reveal_chapter"]:
                    debts.append({
                        "id": f.get("id", ""),
                        "description": f.get("description", ""),
                        "planted_chapter": f.get("plant_chapter"),
                        "expected_reveal": f.get("reveal_chapter"),
                        "overdue_by": self.chapter_num - f["reveal_chapter"],
                    })

        return debts
```

### _git_backup（Step 6）

```python
async def _git_backup(self, context: dict) -> dict:
    """Git 自动提交（可选）。"""
    project_root = Path(context.get("project_root", "."))
    chapter_num = context.get("chapter_num", 1)

    # 检查配置
    config_path = project_root / ".webnovel" / "config.json"
    auto_commit = False
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            auto_commit = config.get("auto_git_commit", False)
        except json.JSONDecodeError:
            pass

    if not auto_commit:
        return {
            "skipped": True,
            "reason": "auto_git_commit 未开启",
            "instruction": "Git 备份已跳过（未开启自动提交）",
        }

    # 执行提交
    adapter = ScriptAdapter(project_root=str(project_root))
    message = f"[webnovel] 第{chapter_num}章（write Step 6）"
    result = await adapter.git_commit(message)

    if not result.get("success"):
        # 失败不阻断流程
        return {
            "skipped": False,
            "success": False,
            "error": result.get("error", ""),
            "instruction": f"Git 提交失败（不影响流程）：{result.get('error', '')}",
        }

    return {
        "skipped": False,
        "success": True,
        "commit_hash": result.get("commit_hash"),
        "instruction": f"Git 提交成功：{result.get('commit_hash', '')}",
    }
```

## TDD 验收

- Happy path：Step 5 → 正文保存 + 实体提取 + 摘要生成 + state 更新 → Step 6 auto_commit=True → git commit 成功
- Edge case 1：Step 6 auto_git_commit=False → 跳过，返回 skipped=True
- Edge case 2：Step 5 extract_entities 返回空列表 → 不写入设定集，不报错
- Error case：Step 6 git commit 失败 → success=False，不阻断流程（Skill 仍为 completed）
