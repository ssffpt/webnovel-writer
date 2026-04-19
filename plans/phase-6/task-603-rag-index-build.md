# Task 603: 向量索引构建（后台任务 + 进度推送）

## 目标

实现向量索引构建的后台任务机制，通过 SSE 推送构建进度。

## 涉及文件

- `webnovel-writer/dashboard/rag_config_service.py`（修改，新增构建任务管理）
- `webnovel-writer/dashboard/app.py`（修改，注册构建 API + SSE 事件）

## 依赖

- task-602（ScriptAdapter.rag_build_index 已实现）

## 前置知识

索引构建是耗时操作（几十秒到几分钟），不能阻塞 API 请求。需要：
1. POST 请求启动构建 → 立即返回 task_id
2. 后台 asyncio.Task 执行构建
3. 通过 SSE 推送进度（复用 `/api/events` 端点）
4. GET 请求查询构建状态

## 规格

### RAGConfigService 扩展

```python
import asyncio
from datetime import datetime


class RAGConfigService:
    # ... 已有方法 ...

    # 类级别的构建任务跟踪
    _build_tasks: dict = {}  # {task_id: {"status": ..., "progress": ..., ...}}

    async def start_build_index(self, sse_callback=None) -> dict:
        """启动后台索引构建任务。

        Args:
            sse_callback: 可选，SSE 推送回调 (event_data: dict) -> None

        Returns:
            {"task_id": str, "status": "started"}
        """
        import uuid
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
            latest_id = max(self._build_tasks.keys(), key=lambda k: self._build_tasks[k].get("started_at", ""))
            return {"task_id": latest_id, **self._build_tasks[latest_id]}

        return {"task_id": None, "status": "none", "message": "无构建任务"}
```

### API 端点

```python
@app.post("/api/rag/build")
async def start_rag_build(project_root: str):
    """启动索引构建。"""
    service = RAGConfigService(project_root)

    # SSE 回调：通过全局 event_bus 推送
    def sse_callback(event_data):
        # 复用现有 SSE 机制（Phase 0 task-005 实现的 event_bus）
        event_bus.publish(event_data)

    return await service.start_build_index(sse_callback=sse_callback)

@app.get("/api/rag/build/status")
async def get_rag_build_status(project_root: str, task_id: str = None):
    """查询构建状态。"""
    service = RAGConfigService(project_root)
    return service.get_build_status(task_id)
```

### SSE 事件格式

构建进度事件：
```json
{
    "type": "rag.build_progress",
    "task_id": "abc12345",
    "progress": 0.45,
    "message": "正在处理设定集文件..."
}
```

构建完成事件：
```json
{
    "type": "rag.build_completed",
    "task_id": "abc12345",
    "status": "completed",
    "message": "索引构建完成，共 156 个文档",
    "result": {
        "success": true,
        "doc_count": 156,
        "build_time_seconds": 45.2
    }
}
```

## TDD 验收

- Happy path：POST /api/rag/build → 返回 task_id → GET status → progress 递增 → 最终 completed
- Edge case 1：重复启动 → 返回 already_running
- Edge case 2：构建失败 → status="failed" + error 信息
- Error case：无 RAG 配置 → rag_build_index 返回 success=False
