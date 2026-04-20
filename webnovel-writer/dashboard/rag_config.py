"""RAG 配置管理."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class RAGConfig:
    def __init__(self, project_root: str = ""):
        self.project_root = Path(project_root) if project_root else Path(".")
        self.env_path = self.project_root / ".env"
        self.config_path = self.project_root / ".webnovel" / "rag_config.json"

    # -----------------------------------------------------------------
    # 配置读写
    # -----------------------------------------------------------------

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取 RAG 配置项，优先从 .env 读取。"""
        # 1. 尝试 .env
        if self.env_path.exists():
            for line in self.env_path.read_text().splitlines():
                if line.startswith(f"{key}="):
                    value = line.split("=", 1)[1]
                    return value.strip().strip('"').strip("'")
        # 2. 尝试 rag_config.json
        if self.config_path.exists():
            try:
                cfg = json.loads(self.config_path.read_text())
                return cfg.get(key, default)
            except json.JSONDecodeError:
                pass
        return default

    def get_openai_key(self) -> Optional[str]:
        return self.get("OPENAI_API_KEY")

    def get_embedding_model(self) -> str:
        return self.get("RAG_EMBEDDING_MODEL", "text-embedding-3-small")

    def get_chunk_size(self) -> int:
        return int(self.get("RAG_CHUNK_SIZE", "500"))

    def get_chunk_overlap(self) -> int:
        return int(self.get("RAG_CHUNK_OVERLAP", "50"))

    def is_rag_enabled(self) -> bool:
        return self.get("RAG_ENABLED", "false").lower() == "true"

    def set(self, key: str, value: str) -> None:
        """设置配置项（仅更新 rag_config.json）。"""
        cfg = {}
        if self.config_path.exists():
            try:
                cfg = json.loads(self.config_path.read_text())
            except json.JSONDecodeError:
                pass
        cfg[key] = value
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))

    # -----------------------------------------------------------------
    # 索引构建任务管理 (Task 603)
    # -----------------------------------------------------------------

    # 类级别的构建任务跟踪
    _build_tasks: dict = {}  # {task_id: {"status": ..., "progress": ..., ...}}

    async def start_build_index(self, sse_callback=None) -> dict:
        """启动后台索引构建任务。

        Args:
            sse_callback: 可选，SSE 推送回调 (event_data: dict) -> None

        Returns:
            {"task_id": str, "status": "started"}
        """
        task_id = str(uuid.uuid4())[:8]

        # 检查是否已有构建任务在运行
        running = [t for t in self._build_tasks.values() if t["status"] == "running"]
        if running:
            return {"task_id": None, "status": "already_running", "message": "已有构建任务在运行"}

        # 初始化任务状态
        self._build_tasks[task_id] = {
            "status": "running",
            "progress": 0.0,
            "message": "开始构建索引...",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "result": None,
        }

        # 启动后台任务
        asyncio.create_task(self._run_build(task_id, sse_callback))

        return {"task_id": task_id, "status": "started"}

    async def _run_build(self, task_id: str, sse_callback=None) -> None:
        """后台执行索引构建。"""
        from .script_adapter import ScriptAdapter

        task = self._build_tasks[task_id]
        adapter = ScriptAdapter(project_root=str(self.project_root))

        def on_progress(progress: float, message: str):
            task["progress"] = progress
            task["message"] = message
            if sse_callback:
                sse_callback({
                    "type": "rag.build_progress",
                    "task_id": task_id,
                    "progress": progress,
                    "message": message,
                })

        try:
            on_progress(0.1, "扫描项目文件...")
            result = await adapter.rag_build_index(on_progress=on_progress)

            if result["success"]:
                task["status"] = "completed"
                task["progress"] = 1.0
                task["message"] = f"索引构建完成，共 {result['doc_count']} 个文档"
                task["result"] = result
            else:
                task["status"] = "failed"
                task["message"] = f"构建失败：{result.get('error', '未知错误')}"
                task["result"] = result

        except Exception as e:
            task["status"] = "failed"
            task["message"] = f"构建异常：{str(e)}"

        task["completed_at"] = datetime.now().isoformat()

        # 推送完成事件
        if sse_callback:
            sse_callback({
                "type": "rag.build_completed",
                "task_id": task_id,
                "status": task["status"],
                "message": task["message"],
                "result": task.get("result"),
            })

    def get_build_status(self, task_id: str = None) -> dict:
        """查询构建任务状态。

        Args:
            task_id: 指定任务 ID，为 None 时返回最近的任务

        Returns:
            {
                "task_id": str,
                "status": "running" | "completed" | "failed",
                "progress": float,
                "message": str,
                "started_at": str,
                "completed_at": str | None,
                "result": dict | None,
            }
        """
        if task_id and task_id in self._build_tasks:
            return {"task_id": task_id, **self._build_tasks[task_id]}

        # 返回最近的任务
        if self._build_tasks:
            latest_id = max(
                self._build_tasks.keys(),
                key=lambda k: self._build_tasks[k].get("started_at", ""),
            )
            return {"task_id": latest_id, **self._build_tasks[latest_id]}

        return {"task_id": None, "status": "none", "message": "无构建任务"}