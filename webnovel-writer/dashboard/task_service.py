from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock, Thread
from uuid import uuid4

from .claude_runner import run_action
from .models import TASK_IDLE_PAYLOAD


class TaskService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._tasks: dict[str, dict] = {}
        self._current_task_id: str | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe_events(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=128)
        self._subscribers.append(q)
        return q

    def unsubscribe_events(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def create_task(self, action: dict, context: dict | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        task = {
            "id": uuid4().hex,
            "status": "pending",
            "action": deepcopy(action),
            "context": deepcopy(context or {}),
            "createdAt": now,
            "updatedAt": now,
            "logs": [],
            "result": None,
            "error": None,
        }
        with self._lock:
            self._tasks[task["id"]] = task
            self._current_task_id = task["id"]
        self._emit_task_event(task)
        created_snapshot = deepcopy(task)
        Thread(
            target=self._execute_task,
            args=(task["id"],),
            daemon=True,
        ).start()
        return created_snapshot

    def get_task(self, task_id: str) -> dict | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return deepcopy(task) if task else None

    def get_current_task(self) -> dict:
        with self._lock:
            if self._current_task_id and self._current_task_id in self._tasks:
                return deepcopy(self._tasks[self._current_task_id])
        return deepcopy(TASK_IDLE_PAYLOAD)

    def append_log(self, task_id: str, message: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task["logs"].append(
                {
                    "message": message,
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                }
            )
            task["logs"] = task["logs"][-200:]
            task["updatedAt"] = datetime.now(timezone.utc).isoformat()
            snapshot = deepcopy(task)
        self._emit_task_event(snapshot)

    def mark_running(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task["status"] = "running"
            task["updatedAt"] = datetime.now(timezone.utc).isoformat()
            snapshot = deepcopy(task)
        self._emit_task_event(snapshot)

    def mark_completed(self, task_id: str, result: dict | None = None) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task["status"] = "completed"
            task["result"] = deepcopy(result)
            task["error"] = None
            task["updatedAt"] = datetime.now(timezone.utc).isoformat()
            snapshot = deepcopy(task)
        self._emit_task_event(snapshot)

    def mark_failed(self, task_id: str, error: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task["status"] = "failed"
            task["error"] = error
            task["updatedAt"] = datetime.now(timezone.utc).isoformat()
            snapshot = deepcopy(task)
        self._emit_task_event(snapshot)

    def _execute_task(self, task_id: str) -> None:
        task = self.get_task(task_id)
        if task is None:
            return

        self.mark_running(task_id)
        self.append_log(task_id, "任务开始执行")

        try:
            execution = run_action(task["action"], task.get("context"))
            if execution.get("stdout"):
                self.append_log(task_id, execution["stdout"])
            if execution.get("success"):
                self.mark_completed(task_id, execution.get("result"))
                self.append_log(task_id, "任务执行完成")
            else:
                error = execution.get("stderr") or "任务执行失败"
                self.mark_failed(task_id, error)
                self.append_log(task_id, error)
        except Exception as exc:  # pragma: no cover - 容错保护
            self.mark_failed(task_id, str(exc))
            self.append_log(task_id, f"任务异常：{exc}")

    def _emit_task_event(self, task: dict) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        message = json.dumps(
            {
                "type": "task.updated",
                "taskId": task["id"],
                "task": deepcopy(task),
            },
            ensure_ascii=False,
        )
        self._loop.call_soon_threadsafe(self._dispatch, message)

    def _dispatch(self, message: str) -> None:
        dead: list[asyncio.Queue] = []
        for q in self._subscribers:
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe_events(q)
