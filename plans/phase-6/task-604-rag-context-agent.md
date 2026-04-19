# Task 604: Context Agent RAG 模式集成

## 目标

修改 Phase 3 的 Context Agent（context_builder.py），在 RAG 可用时使用向量检索增强上下文质量。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/context_builder.py`（修改）

## 依赖

- task-603（RAG 索引构建可用）
- task-602（ScriptAdapter.rag_search / rag_is_available 已实现）
- Phase 3 task-303（ContextBuilder 已实现降级模式）

## 前置知识

Phase 3 task-303 中 ContextBuilder 的当前逻辑：

```python
class ContextBuilder:
    async def build(self) -> dict:
        # 尝试 extract_chapter_context.py
        ctx_data = await self.adapter.extract_chapter_context(...)
        if not ctx_data.get("success") or ctx_data.get("fallback"):
            # 降级模式：文件系统直接读取
            ctx_data = await self.adapter.load_file_context(...)
            rag_mode = "degraded"
        ...
```

现在需要在 extract_chapter_context 和 load_file_context 之间插入 RAG 检索层。

## 规格

### ContextBuilder 修改

```python
class ContextBuilder:
    async def build(self) -> dict:
        """构建完整写作上下文。

        优先级：
        1. extract_chapter_context.py（含 RAG）— 最完整
        2. RAG 检索 + 文件系统 — RAG 可用但 script 不可用
        3. 纯文件系统 — 降级模式
        """
        # 尝试通过 ScriptAdapter 获取上下文
        ctx_data = await self.adapter.extract_chapter_context(
            chapter_num=self.chapter_num,
            context_window=5,
        )

        rag_mode = "full"

        if not ctx_data.get("success") or ctx_data.get("fallback"):
            # Script 不可用，检查 RAG 是否可用
            if self.adapter.rag_is_available():
                # RAG 模式：文件系统 + 向量检索
                ctx_data = await self._build_with_rag()
                rag_mode = "rag"
            else:
                # 纯降级模式
                ctx_data = await self.adapter.load_file_context(
                    chapter_num=self.chapter_num,
                    context_window=5,
                )
                rag_mode = "degraded"

        # 构建 7 板块任务书
        task_brief = self._build_task_brief(ctx_data)

        # 构建 Context Contract
        contract = self._build_context_contract(ctx_data)

        # 构建写作执行包
        execution_pack = self._build_execution_pack(task_brief, contract)

        self.context["task_brief"] = task_brief
        self.context["context_contract"] = contract
        self.context["execution_pack"] = execution_pack
        self.context["rag_mode"] = rag_mode

        return {
            "task_brief": task_brief,
            "context_contract": contract,
            "rag_mode": rag_mode,
            "instruction": self._get_mode_instruction(rag_mode),
        }

    async def _build_with_rag(self) -> dict:
        """RAG 模式：文件系统基础数据 + 向量检索增强。"""
        # 1. 先加载文件系统基础数据
        base_data = await self.adapter.load_file_context(
            chapter_num=self.chapter_num,
            context_window=5,
        )

        # 2. 构建 RAG 查询
        queries = self._build_rag_queries()

        # 3. 执行向量检索
        rag_results = {}
        for query_name, query_text in queries.items():
            result = await self.adapter.rag_search(query=query_text, top_k=5)
            if result.get("success"):
                rag_results[query_name] = result.get("results", [])

        # 4. 将 RAG 结果合并到基础数据
        enriched = self._merge_rag_results(base_data, rag_results)

        return enriched

    def _build_rag_queries(self) -> dict:
        """构建 RAG 检索查询。

        针对写作需要的不同维度，生成多个查询：
        - 相关设定：与本章大纲相关的设定片段
        - 相关伏笔：与本章角色/事件相关的伏笔
        - 前文关联：与本章场景/角色相关的前文片段
        """
        # 从本章大纲中提取关键信息
        outline = self.context.get("task_brief", {}).get("chapter_outline", "")
        if not outline:
            # 尝试从文件系统加载
            outline_dir = self.project_root / "大纲"
            for vol_dir in outline_dir.iterdir() if outline_dir.exists() else []:
                if vol_dir.is_dir():
                    ch_file = vol_dir / f"第{self.chapter_num}章.json"
                    if ch_file.exists():
                        import json
                        try:
                            data = json.loads(ch_file.read_text(encoding="utf-8"))
                            outline = data.get("summary", "")
                        except json.JSONDecodeError:
                            pass
                        break

        queries = {}

        if outline:
            queries["related_settings"] = f"设定 角色能力 力量等级 {outline[:200]}"
            queries["related_foreshadowing"] = f"伏笔 暗线 悬念 {outline[:200]}"
            queries["related_context"] = f"前文 场景 {outline[:200]}"

        return queries

    def _merge_rag_results(self, base_data: dict, rag_results: dict) -> dict:
        """将 RAG 检索结果合并到基础数据。"""
        enriched = {**base_data}
        enriched["fallback"] = False  # 不再是降级模式

        # 合并相关设定
        if "related_settings" in rag_results:
            rag_settings = "\n\n".join(
                f"[RAG] {r['text']}" for r in rag_results["related_settings"]
            )
            enriched["settings"] = enriched.get("settings", "") + "\n\n" + rag_settings

        # 合并相关伏笔
        if "related_foreshadowing" in rag_results:
            rag_foreshadowing = [
                {"source": "rag", "text": r["text"], "score": r.get("score", 0)}
                for r in rag_results["related_foreshadowing"]
            ]
            enriched["foreshadowing"] = enriched.get("foreshadowing", []) + rag_foreshadowing

        # 合并前文关联
        if "related_context" in rag_results:
            rag_context = [r["text"] for r in rag_results["related_context"]]
            enriched["previous_summaries"] = enriched.get("previous_summaries", []) + rag_context

        return enriched

    def _get_mode_instruction(self, rag_mode: str) -> str:
        """根据模式返回说明文本。"""
        if rag_mode == "full":
            return "上下文构建完成（完整模式）"
        elif rag_mode == "rag":
            return "上下文构建完成（RAG 增强模式）"
        else:
            return "上下文构建完成（RAG 未配置，使用文件系统降级模式）"
```

### Data Agent 增量索引

修改 Phase 3 task-307 的 DataAgent，在保存章节后增量更新 RAG 索引：

```python
class DataAgent:
    async def run(self) -> dict:
        # ... 已有流水线 ...

        # 8. 增量更新 RAG 索引（如果可用）
        if self.adapter.rag_is_available():
            chapter_path = self.context.get("chapter_path", "")
            if chapter_path:
                await self.adapter.rag_add_doc(chapter_path, doc_type="chapter")
                results["rag_indexed"] = True

        return { ... }
```

## TDD 验收

- Happy path：RAG 可用 → ContextBuilder 使用 _build_with_rag → rag_mode="rag" → settings 包含 [RAG] 标记的内容
- Edge case 1：RAG 不可用 → 降级为文件系统 → rag_mode="degraded"
- Edge case 2：RAG 检索返回空结果 → 合并后数据与降级模式相同，不报错
- Error case：rag_search 失败 → 跳过该查询维度，使用基础数据
