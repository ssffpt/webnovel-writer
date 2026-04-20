#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ScriptAdapter — Python API wrapper for scripts/ CLI tools.

Provides async methods that invoke scripts/ CLI tools via subprocess,
with structured error handling, timeout control, and JSON parsing.

Used by SkillRunner to execute write/review/data tasks without
direct subprocess calls scattered across skill handlers.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


class ScriptAdapter:
    """Wrapper for CLI tools in scripts/."""

    def __init__(self, project_root: str = ""):
        self.project_root = Path(project_root) if project_root else Path(".")

    # -------------------------------------------------------------------------
    # Skeleton methods (from task-104)
    # -------------------------------------------------------------------------

    async def init_project(self, **kwargs) -> dict:
        """封装 init_project.py 调用。

        Args:
            title: 小说标题
            genre: 题材类型
            protagonist_name: 主角姓名
            target_words: 目标字数
            target_chapters: 目标章节数
            golden_finger_name: 金手指名称
            golden_finger_type: 金手指类型
            golden_finger_style: 金手指风格
            core_selling_points: 核心卖点
            protagonist_structure: 主角结构
            heroine_config: 女主配置
            heroine_names: 女主姓名
            heroine_role: 女主定位
            co_protagonists: 多主角姓名
            co_protagonist_roles: 多主角定位
            antagonist_tiers: 反派分层
            world_scale: 世界规模
            factions: 势力格局
            power_system_type: 力量体系类型
            social_class: 社会阶层
            resource_distribution: 资源分配
            gf_visibility: 金手指可见度
            gf_irreversible_cost: 金手指不可逆代价
            protagonist_desire: 主角欲望
            protagonist_flaw: 主角缺陷
            protagonist_archetype: 主角人设类型
            antagonist_level: 反派等级
            target_reader: 目标读者
            platform: 发布平台
            currency_system: 货币体系
            currency_exchange: 货币兑换规则
            sect_hierarchy: 宗门层级
            cultivation_chain: 境界链
            cultivation_subtiers: 小境界划分

        Returns:
            {"success": True, "project_root": str} 或 {"success": False, "error": str}
        """
        script = _SCRIPTS_DIR / "init_project.py"
        cmd = [
            sys.executable, str(script),
            str(self.project_root),
            kwargs.get("title", ""),
            kwargs.get("genre", ""),
        ]

        # 可选参数映射
        optional_args = [
            ("--protagonist-name", kwargs.get("protagonist_name")),
            ("--target-words", kwargs.get("target_words")),
            ("--target-chapters", kwargs.get("target_chapters")),
            ("--golden-finger-name", kwargs.get("golden_finger_name")),
            ("--golden-finger-type", kwargs.get("golden_finger_type")),
            ("--golden-finger-style", kwargs.get("golden_finger_style")),
            ("--core-selling-points", kwargs.get("core_selling_points")),
            ("--protagonist-structure", kwargs.get("protagonist_structure")),
            ("--heroine-config", kwargs.get("heroine_config")),
            ("--heroine-names", kwargs.get("heroine_names")),
            ("--heroine-role", kwargs.get("heroine_role")),
            ("--co-protagonists", kwargs.get("co_protagonists")),
            ("--co-protagonist-roles", kwargs.get("co_protagonist_roles")),
            ("--antagonist-tiers", kwargs.get("antagonist_tiers")),
            ("--world-scale", kwargs.get("world_scale")),
            ("--factions", kwargs.get("factions")),
            ("--power-system-type", kwargs.get("power_system_type")),
            ("--social-class", kwargs.get("social_class")),
            ("--resource-distribution", kwargs.get("resource_distribution")),
            ("--gf-visibility", kwargs.get("gf_visibility")),
            ("--gf-irreversible-cost", kwargs.get("gf_irreversible_cost")),
            ("--protagonist-desire", kwargs.get("protagonist_desire")),
            ("--protagonist-flaw", kwargs.get("protagonist_flaw")),
            ("--protagonist-archetype", kwargs.get("protagonist_archetype")),
            ("--antagonist-level", kwargs.get("antagonist_level")),
            ("--target-reader", kwargs.get("target_reader")),
            ("--platform", kwargs.get("platform")),
            ("--currency-system", kwargs.get("currency_system")),
            ("--currency-exchange", kwargs.get("currency_exchange")),
            ("--sect-hierarchy", kwargs.get("sect_hierarchy")),
            ("--cultivation-chain", kwargs.get("cultivation_chain")),
            ("--cultivation-subtiers", kwargs.get("cultivation_subtiers")),
        ]
        for flag, value in optional_args:
            if value is not None and value != "":
                cmd.extend([flag, str(value)])

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, encoding="utf-8", timeout=120,
            )
        except Exception as exc:
            return {"success": False, "error": f"subprocess error: {exc}"}

        if result.returncode != 0:
            return {"success": False, "error": result.stderr or result.stdout}
        return {"success": True, "project_root": str(self.project_root)}

    async def patch_outline(self, project_root: str, **kwargs) -> None:
        """后处理：补齐总纲内容。

        在总纲.md 中追加以下章节（若尚不存在对应标题）：
        - 故事一句话
        - 核心冲突
        - 反派分层
        """
        outline_path = Path(project_root) / "大纲" / "总纲.md"
        if not outline_path.exists():
            return

        content = outline_path.read_text(encoding="utf-8")
        patches: list[str] = []

        if kwargs.get("one_line_story") and "故事一句话" not in content:
            patches.append(f"\n\n## 故事一句话\n\n{kwargs['one_line_story']}\n")
        if kwargs.get("core_conflict") and "核心冲突" not in content:
            patches.append(f"\n\n## 核心冲突\n\n{kwargs['core_conflict']}\n")
        if kwargs.get("villain_tiers") and "反派分层" not in content:
            patches.append(f"\n\n## 反派分层\n\n{kwargs['villain_tiers']}\n")

        if patches:
            outline_path.write_text(content + "".join(patches), encoding="utf-8")

    async def write_idea_bank(self, project_root: str, package: dict) -> None:
        """写入 .webnovel/idea_bank.json。"""
        idea_bank_path = Path(project_root) / ".webnovel" / "idea_bank.json"
        idea_bank_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "creativity_package": package,
            "created_at": datetime.now().isoformat(),
        }
        idea_bank_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # Core methods
    # -------------------------------------------------------------------------

    async def extract_chapter_context(
        self,
        chapter_num: int,
        context_window: int = 5,
    ) -> dict:
        """封装 extract_chapter_context.py 调用。

        Args:
            chapter_num: 目标章节编号
            context_window: 前文窗口大小（默认前 5 章）

        Returns:
            {
                "success": True,
                "chapter": int,
                "outline": str,
                "previous_summaries": list[str],
                "state_summary": str,
                "context_contract_version": str | None,
                "context_weight_stage": str | None,
                "reader_signal": dict,
                "genre_profile": dict,
                "writing_guidance": dict,
                "rag_assist": dict,
            }
            or on error:
            {"success": False, "error": str, "fallback": True}
        """
        script = _SCRIPTS_DIR / "extract_chapter_context.py"
        cmd = [
            sys.executable, str(script),
            "--project-root", str(self.project_root),
            "--chapter", str(chapter_num),
            "--format", "json",
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=60,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or result.stdout,
                "fallback": True,
            }

        try:
            payload = json.loads(result.stdout)
            payload["success"] = True
            return payload
        except json.JSONDecodeError:
            # stdout 不是 JSON，作为纯文本返回
            return {"success": True, "raw_context": result.stdout, "fallback": True}

    async def extract_entities(self, chapter_path: str) -> dict:
        """Extract entities from a chapter file.

        Returns:
            {
                "success": True,
                "entities": [
                    {"name": "张三", "type": "character", "attributes": {...}},
                    ...
                ]
            }
        """
        script = _SCRIPTS_DIR / "data_modules" / "entity_linker.py"
        cmd = [
            sys.executable, str(script),
            "--chapter-path", chapter_path,
            "--format", "json",
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=120,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr, "entities": []}

        try:
            return {"success": True, **json.loads(result.stdout)}
        except json.JSONDecodeError:
            return {"success": True, "entities": [], "raw": result.stdout}

    async def generate_summary(self, chapter_path: str) -> dict:
        """Generate a chapter summary.

        Returns:
            {"success": True, "summary": str, "key_events": list[str]}
        """
        # summary_generator.py does not exist as a standalone CLI;
        # use extract_chapter_context with --chapter to get summary from context
        script = _SCRIPTS_DIR / "extract_chapter_context.py"
        cmd = [
            sys.executable, str(script),
            "--project-root", str(self.project_root),
            "--chapter", chapter_path,
            "--format", "json",
        ]

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=120,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr, "summary": ""}

        try:
            payload = json.loads(result.stdout)
            # extract_chapter_context returns state_summary as the summary-like field
            return {
                "success": True,
                "summary": payload.get("state_summary", ""),
                "key_events": [],
            }
        except json.JSONDecodeError:
            return {"success": True, "summary": result.stdout.strip()}

    async def update_state(self, updates: dict) -> dict:
        """封装 update_state.py 调用。

        Args:
            updates: 要更新的字段 dict; keys match update_state.py CLI flags:
                --protagonist-power, --protagonist-location, --golden-finger,
                --relationship, --add-foreshadowing, --resolve-foreshadowing,
                --progress, --volume-planned, --add-review, --strand-dominant

        Returns:
            {"success": bool, "updated_fields": list[str]}
        """
        script = _SCRIPTS_DIR / "update_state.py"
        cmd = [sys.executable, str(script), "--project-root", str(self.project_root)]

        # Build CLI args from updates dict
        arg_map = {
            "protagonist_power": "--protagonist-power",
            "protagonist_location": "--protagonist-location",
            "golden_finger": "--golden-finger",
            "progress": "--progress",
            "volume_planned": "--volume-planned",
            "chapters_range": "--chapters-range",
            "add_review": "--add-review",
            "strand_dominant": "--strand-dominant",
        }

        for key, value in updates.items():
            flag = arg_map.get(key)
            if flag is None:
                continue
            if key == "progress" and isinstance(value, (list, tuple)):
                cmd.extend([flag, str(value[0]), str(value[1])])
            elif key == "protagonist_power" and isinstance(value, (list, tuple)):
                cmd.extend([flag, value[0], str(value[1]), str(value[2])])
            elif key == "protagonist_location" and isinstance(value, (list, tuple)):
                cmd.extend([flag, value[0], str(value[1])])
            elif key == "golden_finger" and isinstance(value, (list, tuple)):
                cmd.extend([flag, value[0], str(value[1]), str(value[2])])
            elif key == "strand_dominant" and isinstance(value, (list, tuple)):
                cmd.extend([flag, value[0], str(value[1])])
            elif key == "volume_planned":
                cmd.extend([flag, str(value)])
            elif key == "add_foreshadowing" and isinstance(value, (list, tuple)):
                cmd.extend(["--add-foreshadowing", value[0], value[1]])
            elif key == "resolve_foreshadowing" and isinstance(value, (list, tuple)):
                cmd.extend(["--resolve-foreshadowing", value[0], str(value[1])])
            elif key == "relationship" and isinstance(value, dict):
                for char_name, attrs in value.items():
                    for attr_key, attr_val in attrs.items():
                        cmd.extend(["--relationship", char_name, attr_key, str(attr_val)])
            elif key == "add_review" and isinstance(value, (list, tuple)):
                cmd.extend(["--add-review", value[0], value[1]])

        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True,
            encoding="utf-8", timeout=30,
        )

        if result.returncode != 0:
            return {"success": False, "error": result.stderr}

        return {"success": True, "updated_fields": list(updates.keys())}

    async def git_commit(self, message: str) -> dict:
        """Execute git add + commit.

        Returns:
            {"success": bool, "commit_hash": str | None, "error": str | None}
        """
        cmd_add = ["git", "-C", str(self.project_root), "add", "-A"]
        cmd_commit = ["git", "-C", str(self.project_root), "commit", "-m", message]

        result_add = await asyncio.to_thread(
            subprocess.run, cmd_add, capture_output=True, text=True, encoding="utf-8",
        )
        if result_add.returncode != 0:
            return {"success": False, "error": f"git add failed: {result_add.stderr}"}

        result_commit = await asyncio.to_thread(
            subprocess.run, cmd_commit, capture_output=True, text=True, encoding="utf-8",
        )
        if result_commit.returncode != 0:
            if "nothing to commit" in result_commit.stdout:
                return {"success": True, "commit_hash": None, "message": "nothing to commit"}
            return {"success": False, "error": result_commit.stderr}

        match = re.search(r'\[[\w/]+ ([a-f0-9]+)\]', result_commit.stdout)
        commit_hash = match.group(1) if match else None

        return {"success": True, "commit_hash": commit_hash}

    async def load_file_context(
        self,
        chapter_num: int,
        context_window: int = 5,
    ) -> dict:
        """RAG 降级模式：直接从文件系统加载上下文。

        当 extract_chapter_context.py 不可用或无 RAG 时使用。
        从文件系统读取总纲 + 设定集 + 前 N 章摘要。

        Returns: 与 extract_chapter_context 相同的结构
        """
        project_root = self.project_root

        # Load main outline
        outline_path = project_root / "大纲" / "总纲.md"
        outline = outline_path.read_text(encoding="utf-8") if outline_path.exists() else ""

        # Load settings
        settings_text = ""
        setting_dir = project_root / "设定集"
        if setting_dir.exists():
            for f in sorted(setting_dir.glob("*.md")):
                settings_text += f"\n\n## {f.stem}\n\n{f.read_text(encoding='utf-8')}"

        # Load previous summaries
        summaries = []
        summary_dir = project_root / ".webnovel" / "summaries"
        if summary_dir.exists():
            start = max(1, chapter_num - context_window)
            for i in range(start, chapter_num):
                sp = summary_dir / f"ch{i:04d}.md"
                if sp.exists():
                    content = sp.read_text(encoding="utf-8")
                    # Extract summary section
                    m = re.search(
                        r"##\s*剧情摘要\s*\r?\n(.+?)(?=\r?\n##|$)",
                        content,
                        re.DOTALL,
                    )
                    summaries.append(
                        (m.group(1) if m else content).strip()
                    )

        # Load chapter outline
        chapter_outline = ""
        outline_dir = project_root / "大纲"
        if outline_dir.exists():
            for vol_dir in outline_dir.iterdir():
                if vol_dir.is_dir():
                    ch_file = vol_dir / f"第{chapter_num}章.md"
                    if ch_file.exists():
                        chapter_outline = ch_file.read_text(encoding="utf-8")
                        break

        return {
            "success": True,
            "fallback": True,
            "outline": chapter_outline or outline,
            "settings": settings_text,
            "previous_summaries": summaries,
            "foreshadowing": [],
            "character_states": {},
            "constraints": "",
        }

    # -------------------------------------------------------------------------
    # RAG methods (Task 602)
    # -------------------------------------------------------------------------

    async def build_index(self, project_root: str, force: bool = False) -> dict:
        """封装 scripts/build_rag_index.py 调用。

        Args:
            project_root: 项目根目录
            force: 是否强制重建（传递 --force flag）

        Returns:
            {"success": bool, "chunk_count": int | None, "error": str | None}
        """
        script = _SCRIPTS_DIR / "build_rag_index.py"
        if not script.exists():
            return {"success": False, "error": "build_rag_index.py not found"}

        cmd = [sys.executable, str(script), str(project_root)]
        if force:
            cmd.append("--force")

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True,
                encoding="utf-8", timeout=300,
            )
        except Exception as exc:
            return {"success": False, "error": f"subprocess error: {exc}"}

        if result.returncode != 0:
            return {"success": False, "error": result.stderr or result.stdout}

        try:
            payload = json.loads(result.stdout)
            return {"success": True, "chunk_count": payload.get("chunks", 0)}
        except json.JSONDecodeError:
            return {"success": True, "chunk_count": 0}

    async def query_rag(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> dict:
        """RAG 查询方法。在已构建的向量索引中检索相关内容。

        Args:
            query: 查询文本
            top_k: 返回前 K 条结果
            filters: 可选过滤条件（如 {"chapter_range": [1, 10]}）

        Returns:
            {"success": bool, "results": list[dict] | None, "fallback": bool, ...}
        """
        script = _SCRIPTS_DIR / "query_rag.py"
        if not script.exists():
            # Fallback to load_file_context simulation
            return await self.load_file_context(chapter_num=1, context_window=top_k)

        cmd = [
            sys.executable, str(script),
            "--query", query,
            "--top-k", str(top_k),
        ]
        if filters:
            for key, val in filters.items():
                cmd.extend(["--filter", json.dumps({key: val})])

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True,
                encoding="utf-8", timeout=60,
            )
        except Exception as exc:
            return {
                "success": False,
                "error": f"subprocess error: {exc}",
                "fallback": True,
            }

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or result.stdout,
                "fallback": True,
            }

        try:
            payload = json.loads(result.stdout)
            return {"success": True, "results": payload.get("results", [])}
        except json.JSONDecodeError:
            return {
                "success": True,
                "results": [],
                "raw": result.stdout,
                "fallback": True,
            }

    def check_index_status(self, project_root: str) -> dict:
        """检查向量索引状态。

        Args:
            project_root: 项目根目录

        Returns:
            {
                "indexed": bool,
                "chunk_count": int,
                "last_updated": str | None,
                "index_size_mb": float | None,
            }
        """
        index_dir = Path(project_root) / ".webnovel" / "rag_index"
        state_file = Path(project_root) / ".webnovel" / "state.json"

        last_updated: str | None = None
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                last_updated = state.get("last_updated")
            except Exception:
                pass

        if not index_dir.exists():
            return {
                "indexed": False,
                "chunk_count": 0,
                "last_updated": last_updated,
                "index_size_mb": None,
            }

        # Count index files and compute size
        index_files = list(index_dir.glob("*"))
        chunk_count = len(index_files)

        index_size_bytes = sum(f.stat().st_size for f in index_files if f.is_file())
        index_size_mb = round(index_size_bytes / (1024 * 1024), 3)

        return {
            "indexed": chunk_count > 0,
            "chunk_count": chunk_count,
            "last_updated": last_updated,
            "index_size_mb": index_size_mb,
        }

    # -------------------------------------------------------------------------
    # RAG methods via rag_adapter.py (Task 602)
    # -------------------------------------------------------------------------

    def _parse_rag_output(self, stdout: str) -> dict:
        """解析 rag_adapter.py 的 CLI JSON 输出。

        rag_adapter.py 使用 cli_output.print_success/print_error，输出格式：
        - 成功: {"status": "success", "data": ..., "message": "..."}
        - 失败: {"status": "error", "error": {"code": "...", "message": "..."}}
        """
        try:
            payload = json.loads(stdout)
            if payload.get("status") == "success":
                return {"ok": True, "data": payload.get("data", {}), "message": payload.get("message", "")}
            elif payload.get("status") == "error":
                err = payload.get("error", {})
                return {"ok": False, "error": err.get("message", "unknown error"), "code": err.get("code", "")}
            else:
                return {"ok": False, "error": f"unexpected output: {stdout[:200]}"}
        except json.JSONDecodeError:
            return {"ok": False, "error": f"invalid JSON: {stdout[:200]}"}

    async def rag_build_index(
        self,
        on_progress: callable = None,
    ) -> dict:
        """构建向量索引。

        扫描项目中的章节文件，逐章调用 rag_adapter.py index-chapter 构建索引。

        Args:
            on_progress: 可选回调 (progress: float, message: str) -> None

        Returns:
            {
                "success": bool,
                "doc_count": int,
                "build_time_seconds": float,
                "error": str | None,
            }
        """
        import time

        start_time = time.time()

        # Scan chapter files
        text_dir = self.project_root / "正文"
        if not text_dir.exists():
            self._write_index_meta(0, 0)
            return {
                "success": True,
                "doc_count": 0,
                "build_time_seconds": 0,
                "error": None,
            }

        chapter_files = sorted(text_dir.glob("第*章.md"))
        if not chapter_files:
            self._write_index_meta(0, 0)
            return {
                "success": True,
                "doc_count": 0,
                "build_time_seconds": 0,
                "error": None,
            }

        total = len(chapter_files)
        indexed = 0

        for i, chapter_file in enumerate(chapter_files):
            # Extract chapter number from filename (e.g., 第0001章.md -> 1)
            match = re.match(r"第(\d+)章", chapter_file.stem)
            if not match:
                continue
            chapter_num = int(match.group(1))

            # Read chapter content
            try:
                content = chapter_file.read_text(encoding="utf-8")
            except Exception:
                continue

            if not content.strip():
                continue

            # Build scenes JSON (single scene per chapter for simplicity)
            scenes = json.dumps([{"index": 1, "content": content}], ensure_ascii=False)

            cmd = [
                sys.executable, "-m", "data_modules.rag_adapter",
                "--project-root", str(self.project_root),
                "index-chapter",
                "--chapter", str(chapter_num),
                "--scenes", scenes,
            ]

            try:
                result = await asyncio.to_thread(
                    subprocess.run, cmd, capture_output=True, text=True,
                    encoding="utf-8", timeout=120, cwd=str(_SCRIPTS_DIR),
                )
            except Exception:
                continue

            if result.returncode == 0:
                parsed = self._parse_rag_output(result.stdout)
                if parsed["ok"]:
                    indexed += 1

            # Report progress
            if on_progress:
                progress = (i + 1) / total
                on_progress(progress, f"已索引 {i + 1}/{total} 章")

        build_time = time.time() - start_time
        self._write_index_meta(indexed, build_time)

        return {
            "success": True,
            "doc_count": indexed,
            "build_time_seconds": round(build_time, 2),
            "error": None,
        }

    async def rag_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> dict:
        """向量检索。

        调用 rag_adapter.py search --query Q --top-k N --mode hybrid

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            {
                "success": bool,
                "results": [
                    {
                        "text": str,
                        "source": str,
                        "score": float,
                        "metadata": dict,
                    },
                ],
                "error": str | None,
            }
        """
        cmd = [
            sys.executable, "-m", "data_modules.rag_adapter",
            "--project-root", str(self.project_root),
            "search",
            "--query", query,
            "--top-k", str(top_k),
            "--mode", "hybrid",
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True,
                encoding="utf-8", timeout=60, cwd=str(_SCRIPTS_DIR),
            )
        except Exception as exc:
            return {"success": False, "results": [], "error": f"subprocess error: {exc}"}

        if result.returncode != 0:
            return {"success": False, "results": [], "error": result.stderr or result.stdout}

        parsed = self._parse_rag_output(result.stdout)
        if not parsed["ok"]:
            return {"success": False, "results": [], "error": parsed.get("error", "unknown")}

        # Transform rag_adapter search results to our format
        raw_results = parsed.get("data", [])
        if not isinstance(raw_results, list):
            raw_results = []

        results = []
        for item in raw_results:
            results.append({
                "text": item.get("content", ""),
                "source": item.get("source_file", ""),
                "score": item.get("score", 0),
                "metadata": {
                    "chapter": item.get("chapter"),
                    "chunk_type": item.get("chunk_type"),
                    "chunk_id": item.get("chunk_id"),
                },
            })

        return {"success": True, "results": results, "error": None}

    async def rag_add_doc(self, doc_path: str, doc_type: str = "chapter") -> dict:
        """增量添加文档到索引。

        对于章节类型，读取文件内容并调用 rag_adapter.py index-chapter。
        对于其他类型，预留接口。

        Args:
            doc_path: 文档路径
            doc_type: 文档类型（chapter/setting/summary）

        Returns:
            {"success": bool, "chunks_added": int}
        """
        if doc_type != "chapter":
            return {"success": True, "chunks_added": 0}

        path = Path(doc_path)
        if not path.exists():
            return {"success": False, "chunks_added": 0, "error": f"file not found: {doc_path}"}

        # Extract chapter number
        match = re.search(r"第(\d+)章", path.stem)
        if not match:
            return {"success": False, "chunks_added": 0, "error": "cannot extract chapter number"}

        chapter_num = int(match.group(1))

        try:
            content = path.read_text(encoding="utf-8")
        except Exception as exc:
            return {"success": False, "chunks_added": 0, "error": str(exc)}

        if not content.strip():
            return {"success": True, "chunks_added": 0}

        scenes = json.dumps([{"index": 1, "content": content}], ensure_ascii=False)

        cmd = [
            sys.executable, "-m", "data_modules.rag_adapter",
            "--project-root", str(self.project_root),
            "index-chapter",
            "--chapter", str(chapter_num),
            "--scenes", scenes,
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True,
                encoding="utf-8", timeout=120, cwd=str(_SCRIPTS_DIR),
            )
        except Exception as exc:
            return {"success": False, "chunks_added": 0, "error": str(exc)}

        if result.returncode != 0:
            return {"success": False, "chunks_added": 0, "error": result.stderr or result.stdout}

        parsed = self._parse_rag_output(result.stdout)
        if not parsed["ok"]:
            return {"success": False, "chunks_added": 0, "error": parsed.get("error", "unknown")}

        data = parsed.get("data", {})
        chunks_added = data.get("stored", 1)

        return {"success": True, "chunks_added": chunks_added}

    def rag_is_available(self) -> bool:
        """检查 RAG 是否可用（有配置 + 有索引元数据）。"""
        from dashboard.rag_config import RAGConfig

        config = RAGConfig(str(self.project_root))

        # Check if RAG is configured (either enabled explicitly or has embedding model)
        has_config = config.is_rag_enabled() or config.get("RAG_EMBEDDING_MODEL") is not None

        # Check if index meta exists
        index_meta = self.project_root / ".webnovel" / "rag" / "index_meta.json"
        has_index = index_meta.exists()

        return has_config and has_index

    def _write_index_meta(self, doc_count: int, build_time: float) -> None:
        """写入索引元数据到 .webnovel/rag/index_meta.json。"""
        meta_dir = self.project_root / ".webnovel" / "rag"
        meta_dir.mkdir(parents=True, exist_ok=True)
        meta_path = meta_dir / "index_meta.json"
        meta = {
            "doc_count": doc_count,
            "build_time_seconds": round(build_time, 2),
            "built_at": datetime.now().isoformat(),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_index_stats(self, project_root: str) -> dict:
        """获取索引统计信息。

        Args:
            project_root: 项目根目录

        Returns:
            {
                "total_chunks": int,
                "total_characters": int,
                "indexed_files": list[str],
                "embedding_model": str,
            }
        """
        stats_file = Path(project_root) / ".webnovel" / "rag_index" / "stats.json"
        if not stats_file.exists():
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "indexed_files": [],
                "embedding_model": "",
            }

        try:
            data = json.loads(stats_file.read_text(encoding="utf-8"))
            return {
                "total_chunks": data.get("total_chunks", 0),
                "total_characters": data.get("total_characters", 0),
                "indexed_files": data.get("indexed_files", []),
                "embedding_model": data.get("embedding_model", ""),
            }
        except Exception:
            return {
                "total_chunks": 0,
                "total_characters": 0,
                "indexed_files": [],
                "embedding_model": "",
            }
