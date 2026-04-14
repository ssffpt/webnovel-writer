"""Phase 1 workbench shared constants."""

WORKBENCH_PAGES = ("overview", "chapters", "outline", "settings")
WORKSPACE_ROOTS = {
    "chapters": "正文",
    "outline": "大纲",
    "settings": "设定集",
}
TASK_STATUSES = (
    "idle",
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
)
TASK_IDLE_PAYLOAD = {
    "status": "idle",
    "task": None,
    "step": None,
    "updatedAt": None,
}
