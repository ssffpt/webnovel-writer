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
            # 降级模式：直接从文件系统加载
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
            "instruction": f"上下文构建完成（{'完整模式' if rag_mode == 'full' else 'RAG 降级模式'}）",
        }

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
