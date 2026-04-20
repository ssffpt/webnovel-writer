"""ContextBuilder — 构建写作上下文（7 板块任务书 + Context Contract）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..script_adapter import ScriptAdapter


class ContextBuilder:
    """构建 7 板块任务书 + Context Contract + 写作执行包。"""

    def __init__(self, context: dict):
        self.context = context
        self.project_root = Path(context.get("project_root", "."))
        self.chapter_num = int(context.get("chapter_num", 1))
        self.adapter = ScriptAdapter(project_root=str(self.project_root))

    async def build(self) -> dict:
        """构建完整写作上下文。

        优先使用 extract_chapter_context.py（含 RAG），
        失败时降级为文件系统直接读取。
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

        # 存入 context 供后续步骤使用
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
            try:
                result = await self.adapter.rag_search(query=query_text, top_k=5)
                if result.get("success"):
                    rag_results[query_name] = result.get("results", [])
            except Exception:
                pass  # 跳过该查询维度

        # 4. 将 RAG 结果合并到基础数据
        enriched = self._merge_rag_results(base_data, rag_results)

        return enriched

    def _build_rag_queries(self) -> dict:
        """构建 RAG 检索查询（多维度）。"""
        # 从文件系统加载本章大纲
        outline = ""
        outline_dir = self.project_root / "大纲"
        if outline_dir.exists():
            for vol_dir in outline_dir.iterdir():
                if vol_dir.is_dir():
                    ch_file = vol_dir / f"第{self.chapter_num}章.md"
                    if ch_file.exists():
                        outline = ch_file.read_text(encoding="utf-8")[:200]
                        break

        queries = {}
        if outline:
            queries["related_settings"] = f"设定 角色能力 力量等级 {outline}"
            queries["related_foreshadowing"] = f"伏笔 暗线 悬念 {outline}"
            queries["related_context"] = f"前文 场景 {outline}"

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
            if rag_settings:
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

    def _build_task_brief(self, ctx_data: dict) -> dict:
        """构建 7 板块任务书。"""
        return {
            "chapter_outline": ctx_data.get("outline", ""),
            "previous_summaries": ctx_data.get("previous_summaries", []),
            "relevant_settings": ctx_data.get("settings", ""),
            "pending_foreshadowing": ctx_data.get("foreshadowing", []),
            "character_states": ctx_data.get("character_states", {}),
            "core_constraints": self._load_core_constraints(ctx_data),
            "style_reference": self._load_style_reference(),
        }

    def _load_core_constraints(self, ctx_data: dict) -> str:
        """加载核心约束：core-constraints + 创意约束包。"""
        constraints = ctx_data.get("constraints", "")

        # 追加创意约束包
        idea_bank_path = self.project_root / ".webnovel" / "idea_bank.json"
        if idea_bank_path.exists():
            try:
                idea_bank = json.loads(idea_bank_path.read_text(encoding="utf-8"))
                pkg = idea_bank.get("creativity_package", {})
                pkg_constraints = pkg.get("constraints", [])
                if pkg_constraints:
                    constraints += "\n\n## 创意约束包\n"
                    for c in pkg_constraints:
                        constraints += f"- [{c.get('type', '')}] {c.get('content', '')}\n"
            except (json.JSONDecodeError, KeyError):
                pass

        return constraints

    def _load_style_reference(self) -> str:
        """加载风格参考样本。"""
        style_path = self.project_root / ".webnovel" / "style_samples"
        if not style_path.exists():
            return ""
        samples = []
        for f in sorted(style_path.glob("*.txt"))[:3]:  # 最多 3 个样本
            samples.append(f.read_text(encoding="utf-8"))
        return "\n---\n".join(samples)

    def _build_context_contract(self, ctx_data: dict) -> dict:
        """构建 Context Contract — 写作约束清单。"""
        return {
            "setting_constraints": self._extract_setting_constraints(ctx_data),
            "foreshadowing_obligations": ctx_data.get("foreshadowing", []),
            "timeline_anchor": self._get_timeline_anchor(),
            "character_boundaries": ctx_data.get("character_states", {}),
        }

    def _extract_setting_constraints(self, ctx_data: dict) -> list[str]:
        """从设定集中提取硬约束。"""
        settings_text = ctx_data.get("settings", "")
        constraints = []
        for line in settings_text.split("\n"):
            line = line.strip()
            if line.startswith("- ") and ("不可" in line or "必须" in line or "禁止" in line):
                constraints.append(line[2:])
        return constraints

    def _get_timeline_anchor(self) -> str:
        """获取当前时间线锚点（上一章结束时的时间点）。"""
        state_path = self.project_root / ".webnovel" / "state.json"
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                return state.get("current_timeline", "")
            except json.JSONDecodeError:
                pass
        return ""

    def _build_execution_pack(self, task_brief: dict, contract: dict) -> dict:
        """构建写作执行包 — 传给 AI 的完整 prompt 上下文。"""
        return {
            "chapter_num": self.chapter_num,
            "task_brief": task_brief,
            "contract": contract,
            "word_target": {"min": 2000, "max": 2500},
            "mode": self.context.get("mode", "standard"),
        }
