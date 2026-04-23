"""
Webnovel Dashboard - FastAPI 主应用

Phase 1 以只读查询为主，并补充 workbench 所需的最小写接口；
所有文件访问都经过 path_guard 防穿越校验。
"""

import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager, closing
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .path_guard import safe_resolve
from .models import TASK_IDLE_PAYLOAD
from .query_service import QueryService
from .task_service import TaskService
from .genre_service import list_genres, list_golden_finger_types
from .project_service import create_project, list_projects, switch_project
from .workbench_service import build_chat_response, build_outline_tree, load_project_summary, save_workspace_file
from .watcher import FileWatcher
from .skill_registry import default_registry
from .skill_models import SkillInstance, StepState
from .skill_runner import SkillRunner
from .rag_config import RAGConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 全局状态
# ---------------------------------------------------------------------------
_project_root: Path | None = None
_watcher = FileWatcher()
_task_service = TaskService()
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent  # webnovel-writer/ 包根目录
_recent_activities: list[dict] = []

# Skill API 全局状态
_active_skills: dict[str, SkillRunner] = {}
_skill_subscribers: list[asyncio.Queue] = []
_rag_subscribers: list[asyncio.Queue] = []

STATIC_DIR = Path(__file__).parent / "frontend" / "dist"


def _get_project_root() -> Path:
    """Return the configured project root (module-level helper, also used by Skill API)."""
    if _project_root is None:
        raise HTTPException(status_code=500, detail="项目根目录未配置")
    return _project_root


async def _restore_active_skills() -> None:
    """Scan .webnovel/workflow/instances/ and restore non-terminal Skill instances.

    Called during app startup so that in-progress workflows (e.g. project init)
    survive server restarts.
    """
    if _project_root is None:
        return
    instances_dir = _project_root / ".webnovel" / "workflow" / "instances"
    if not instances_dir.is_dir():
        return

    from .skill_models import SkillInstance, TERMINAL_STATUSES

    for json_path in sorted(instances_dir.glob("*.json")):
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            instance = SkillInstance.from_dict(data)
        except Exception as exc:
            logger.warning("skip invalid skill instance %s: %s", json_path.name, exc)
            continue

        if instance.status in TERMINAL_STATUSES:
            continue

        try:
            handler = default_registry.get_handler(instance.skill_name)
        except KeyError:
            logger.warning("skip skill instance %s: handler '%s' not registered", instance.id, instance.skill_name)
            continue

        # Rebuild context from completed steps' input_data
        # (confirm steps' input_data is not merged into context by default on restore)
        for ss in instance.step_states:
            if ss.input_data and ss.status in ("done", "completed"):
                instance.context.update(ss.input_data)

        # For confirm steps at waiting_input, re-pre-execute to refresh output_data
        current = instance.current_step()
        if current and current.status == "waiting_input":
            step_def = next((s for s in instance.steps if s.id == current.step_id), None)
            if step_def and step_def.interaction == "confirm":
                try:
                    output_data = await handler.execute_step(current, instance.context)
                    current.output_data = output_data
                except Exception as exc:
                    logger.warning("re-pre-execute for %s failed: %s", current.step_id, exc)

        # Rebuild the on_step_change callback so SSE continues to work
        on_step_change = _make_skill_on_step_change(instance.id, instance.skill_name)
        runner = SkillRunner(instance, handler, on_step_change=on_step_change)
        runner._started = True  # mark as already started so start() won't re-initialise
        _active_skills[instance.id] = runner
        logger.info("restored skill instance %s (status=%s, step=%s)", instance.id, instance.status, instance.current_step_index)


def _webnovel_dir() -> Path:
    return _get_project_root() / ".webnovel"


# ---------------------------------------------------------------------------
# Skill SSE helpers
# ---------------------------------------------------------------------------

async def subscribe_skill_events() -> asyncio.Queue:
    """Add an asyncio.Queue to the skill event subscriber list. Caller must call unsubscribe_skill_events on cleanup."""
    q: asyncio.Queue = asyncio.Queue(maxsize=128)
    _skill_subscribers.append(q)
    return q


def unsubscribe_skill_events(q: asyncio.Queue) -> None:
    """Remove a previously subscribed queue."""
    try:
        _skill_subscribers.remove(q)
    except ValueError:
        pass


def _build_skill_step_event(instance: SkillInstance, step: StepState | None) -> str:
    """Build a JSON string for a skill.step SSE event."""
    step_dict = step.to_dict() if step else None
    return json.dumps(
        {
            "type": "skill.step",
            "skillId": instance.id,
            "skillName": instance.skill_name,
            "step": step_dict,
        },
        ensure_ascii=False,
    )


def _emit_skill_event(message: str) -> None:
    """Dispatch a raw JSON message string to all skill subscribers."""
    for q in _skill_subscribers[:]:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            _skill_subscribers.remove(q)


def _emit_rag_event(message: str) -> None:
    """Dispatch a raw JSON message string to all RAG subscribers."""
    for q in _rag_subscribers[:]:
        try:
            q.put_nowait(message)
        except asyncio.QueueFull:
            _rag_subscribers.remove(q)


async def push_skill_log(skill_id: str, message: str) -> None:
    """Push a skill.log event to all subscribers. Thread-safe via call_soon_threadsafe."""
    payload = json.dumps(
        {"type": "skill.log", "skillId": skill_id, "message": message},
        ensure_ascii=False,
    )
    loop = asyncio.get_running_loop()
    loop.call_soon_threadsafe(lambda: _emit_skill_event(payload))


def _make_skill_on_step_change(skill_id: str, skill_name: str) -> callable:
    """Factory: return an on_step_change callback that emits skill events."""
    def callback(instance: SkillInstance, step: StepState | None) -> None:
        if instance.is_terminal():
            # Emit skill.completed / skill.failed
            if instance.status == "failed":
                err = None
                for st in instance.step_states:
                    if st.error:
                        err = st.error
                        break
                payload = json.dumps(
                    {
                        "type": "skill.failed",
                        "skillId": instance.id,
                        "skillName": instance.skill_name,
                        "error": err or "unknown error",
                    },
                    ensure_ascii=False,
                )
            else:
                # Collect output_data from all completed steps as the result
                result_data = {}
                for st in instance.step_states:
                    if st.output_data:
                        result_data[st.step_id] = st.output_data
                payload = json.dumps(
                    {
                        "type": "skill.completed",
                        "skillId": instance.id,
                        "skillName": instance.skill_name,
                        "result": result_data,
                    },
                    ensure_ascii=False,
                )
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda msg=payload: _emit_skill_event(msg))
        else:
            # Emit skill.step
            msg = _build_skill_step_event(instance, step)
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda m=msg: _emit_skill_event(m))

    return callback


# ---------------------------------------------------------------------------
# Skill API 路由（模块级，便于测试直接调用）
# ---------------------------------------------------------------------------

async def start_skill(skill_name: str, payload: dict) -> dict:
    """POST /api/skill/{skill_name}/start — 启动一个 Skill 实例。"""
    mode = payload.get("mode")
    context = payload.get("context", {})

    try:
        handler = default_registry.get_handler(skill_name)
    except KeyError:
        raise HTTPException(400, f"未注册的 skill: {skill_name}")

    steps = handler.get_steps(mode=mode)
    instance = SkillInstance(
        id=f"{skill_name}-{len(_active_skills) + 1}",
        skill_name=skill_name,
        display_name=default_registry.get_display_name(skill_name),
        status="created",
        project_root=str(_get_project_root()),
        steps=steps,
        step_states=[],
        current_step_index=0,
        mode=mode,
        context=context,
    )
    for step_def in steps:
        instance.step_states.append(StepState(step_id=step_def.id, status="pending"))
    if instance.step_states:
        instance.step_states[0].status = "waiting_input"

    runner = SkillRunner(
        instance,
        handler,
        on_step_change=_make_skill_on_step_change(instance.id, instance.skill_name),
    )
    _active_skills[instance.id] = runner
    asyncio.create_task(runner.start())
    return instance.to_dict()


async def get_skill_status(skill_id: str) -> dict:
    """GET /api/skill/{skill_id}/status — 返回 Skill 实例状态。"""
    runner = _active_skills.get(skill_id)
    if runner is None:
        raise HTTPException(404, "Skill 实例不存在")
    return runner.get_state()


async def submit_skill_step(skill_id: str, payload: dict) -> dict:
    """POST /api/skill/{skill_id}/step — 提交当前 step 的用户输入。"""
    runner = _active_skills.get(skill_id)
    if runner is None:
        raise HTTPException(404, "Skill 实例不存在")
    step_id = payload.get("step_id")
    data = payload.get("data", {})
    await runner.submit_input(step_id, data)
    return runner.get_state()


async def cancel_skill(skill_id: str) -> dict:
    """POST /api/skill/{skill_id}/cancel — 取消 Skill 执行。"""
    runner = _active_skills.get(skill_id)
    if runner is None:
        raise HTTPException(404, "Skill 实例不存在")
    await runner.cancel()
    return {"id": skill_id, "status": "cancelled"}


async def list_active_skills() -> dict:
    """GET /api/skill/active — 返回所有活跃 Skill 实例列表。"""
    return {"instances": [r.get_state() for r in _active_skills.values()]}


async def go_back_skill(skill_id: str, target_step_id: str) -> dict:
    """POST /api/skill/{skill_id}/back — 回退到指定步骤。"""
    runner = _active_skills.get(skill_id)
    if runner is None:
        raise HTTPException(404, "Skill 实例不存在")
    await runner.go_back(target_step_id)
    return runner.get_state()


async def list_pending_skills(skill_name: str | None = None) -> dict:
    """GET /api/skill/pending — 返回未完成的 Skill 实例列表。"""
    results = []
    for skill_id, runner in _active_skills.items():
        instance = runner.instance
        if instance.is_terminal():
            continue
        if skill_name and instance.skill_name != skill_name:
            continue
        current = instance.current_step()
        results.append({
            "id": instance.id,
            "skill_name": instance.skill_name,
            "display_name": instance.display_name,
            "status": instance.status,
            "current_step_index": instance.current_step_index,
            "current_step_id": current.step_id if current else None,
            "current_step_status": current.status if current else None,
            "total_steps": len(instance.step_states),
            "completed_steps": sum(1 for s in instance.step_states if s.status in ("done", "completed")),
            "updated_at": instance.updated_at,
        })
    return {"instances": results}


# ---------------------------------------------------------------------------
# 应用工厂
# ---------------------------------------------------------------------------

def create_app(project_root: str | Path | None = None) -> FastAPI:
    global _project_root

    if project_root:
        _project_root = Path(project_root).resolve()
    elif _project_root is None:
        import os
        env_root = os.environ.get("WEBNOVEL_PROJECT_ROOT")
        if env_root:
            _project_root = Path(env_root).resolve()
        else:
            # Try to restore last used project from workspaces.json
            from .project_service import _read_workspaces
            registry = _read_workspaces()
            last_used = registry.get("last_used_project_root")
            if last_used and Path(last_used).is_dir():
                _project_root = Path(last_used).resolve()

    @asynccontextmanager
    async def _lifespan(_: FastAPI):
        _task_service.set_event_loop(asyncio.get_running_loop())
        if _project_root:
            webnovel = _project_root / ".webnovel"
            if webnovel.is_dir():
                _watcher.start(webnovel, asyncio.get_running_loop())
            await _restore_active_skills()
        try:
            yield
        finally:
            _watcher.stop()

    app = FastAPI(title="Webnovel Dashboard", version="0.1.0", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # ===========================================================
    # API：项目元信息
    # ===========================================================

    @app.get("/api/project/info")
    def project_info():
        """返回 state.json 完整内容（只读）。"""
        if _project_root is None:
            return {"title": None, "genre": None}
        state_path = _webnovel_dir() / "state.json"
        if not state_path.is_file():
            return {"title": None, "genre": None}
        return json.loads(state_path.read_text(encoding="utf-8"))

    @app.get("/api/query/foreshadowing")
    def api_query_foreshadowing(project_root: str | None = None):
        """伏笔查询：三层分类 + 紧急度计算。"""
        root = Path(project_root) if project_root else _get_project_root()
        service = QueryService(str(root))
        return service.query_foreshadowing()

    @app.get("/api/query/golden-finger")
    def api_query_golden_finger(project_root: str | None = None):
        """金手指状态查询。"""
        root = Path(project_root) if project_root else _get_project_root()
        service = QueryService(str(root))
        return service.query_golden_finger()

    @app.get("/api/query/rhythm")
    def api_query_rhythm(project_root: str | None = None, volume_number: int | None = None):
        """节奏分析查询。"""
        root = Path(project_root) if project_root else _get_project_root()
        service = QueryService(str(root))
        return service.query_rhythm(volume_number=volume_number)

    @app.get("/api/query/debt")
    def api_query_debt(project_root: str | None = None):
        """债务查询。"""
        root = Path(project_root) if project_root else _get_project_root()
        service = QueryService(str(root))
        return service.query_debt()

    @app.get("/api/workbench/summary")
    def workbench_summary():
        if _project_root is None:
            return {
                "pages": ["overview", "outline", "settings", "chapters"],
                "project": {"title": None, "genre": None, "target_words": None, "target_chapters": None},
                "progress": {"current_chapter": None, "current_volume": None, "total_words": 0},
                "workspace_roots": [],
                "workspaces": {},
                "recent_tasks": [],
                "recent_changes": [],
                "next_suggestions": [],
            }
        return load_project_summary(_get_project_root())

    def _restart_watcher():
        """重启 FileWatcher 监控当前项目。"""
        _watcher.stop()
        if _project_root:
            webnovel = _project_root / ".webnovel"
            if webnovel.is_dir():
                try:
                    loop = asyncio.get_running_loop()
                    _watcher.start(webnovel, loop)
                except RuntimeError:
                    pass  # 无事件循环（如测试环境），跳过 watcher

    # ===========================================================
    # API：题材与金手指
    # ===========================================================

    @app.get("/api/genres")
    def api_genres():
        return list_genres(_PACKAGE_ROOT)

    @app.get("/api/golden-finger-types")
    def api_golden_finger_types():
        return list_golden_finger_types(_PACKAGE_ROOT)

    # ===========================================================
    # API：项目管理
    # ===========================================================

    @app.post("/api/project/create")
    def api_create_project(payload: dict):
        global _project_root
        title = payload.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            raise HTTPException(400, "title 必填")
        result = create_project(payload, _PACKAGE_ROOT)
        if not result.get("success"):
            raise HTTPException(400, result.get("error", "项目创建失败"))
        _project_root = Path(result["project_root"])
        _restart_watcher()
        return result

    @app.get("/api/projects")
    def api_list_projects():
        return list_projects()

    @app.post("/api/project/switch")
    def api_switch_project(payload: dict):
        global _project_root
        target = payload.get("path", "")
        result = switch_project(target)
        if not result.get("success"):
            raise HTTPException(400, result.get("error", "切换失败"))
        _project_root = Path(result["project_root"])
        _restart_watcher()
        return result

    # ===========================================================
    # API：大纲树与最近动态
    # ===========================================================

    @app.get("/api/outline/tree")
    def api_outline_tree():
        return build_outline_tree(_get_project_root())

    @app.get("/api/recent-activity")
    def api_recent_activity():
        return {"activities": list(_recent_activities[-50:])}

    # ===========================================================
    # API：实体数据库（index.db 只读查询）
    # ===========================================================

    def _get_db() -> sqlite3.Connection:
        db_path = _webnovel_dir() / "index.db"
        if not db_path.is_file():
            raise HTTPException(404, "index.db 不存在")
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _fetchall_safe(conn: sqlite3.Connection, query: str, params: tuple = ()) -> list[dict]:
        """执行只读查询；若目标表不存在（旧库），返回空列表。"""
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.OperationalError as exc:
            if "no such table" in str(exc).lower():
                return []
            raise HTTPException(status_code=500, detail=f"数据库查询失败: {exc}") from exc

    @app.get("/api/entities")
    def list_entities(
        entity_type: str | None = Query(None, alias="type"),
        include_archived: bool = False,
    ):
        """列出所有实体（可按类型过滤）。"""
        with closing(_get_db()) as conn:
            q = "SELECT * FROM entities"
            params: list = []
            clauses: list[str] = []
            if entity_type:
                clauses.append("type = ?")
                params.append(entity_type)
            if not include_archived:
                clauses.append("is_archived = 0")
            if clauses:
                q += " WHERE " + " AND ".join(clauses)
            q += " ORDER BY last_appearance DESC"
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/entities/{entity_id}")
    def get_entity(entity_id: str):
        with closing(_get_db()) as conn:
            row = conn.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
            if not row:
                raise HTTPException(404, "实体不存在")
            return dict(row)

    @app.get("/api/relationships")
    def list_relationships(entity: str | None = None, limit: int = 200):
        with closing(_get_db()) as conn:
            if entity:
                rows = conn.execute(
                    "SELECT * FROM relationships WHERE from_entity = ? OR to_entity = ? ORDER BY chapter DESC LIMIT ?",
                    (entity, entity, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM relationships ORDER BY chapter DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/relationship-events")
    def list_relationship_events(
        entity: str | None = None,
        from_chapter: int | None = None,
        to_chapter: int | None = None,
        limit: int = 200,
    ):
        with closing(_get_db()) as conn:
            q = "SELECT * FROM relationship_events"
            params: list = []
            clauses: list[str] = []
            if entity:
                clauses.append("(from_entity = ? OR to_entity = ?)")
                params.extend([entity, entity])
            if from_chapter is not None:
                clauses.append("chapter >= ?")
                params.append(from_chapter)
            if to_chapter is not None:
                clauses.append("chapter <= ?")
                params.append(to_chapter)
            if clauses:
                q += " WHERE " + " AND ".join(clauses)
            q += " ORDER BY chapter DESC, id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(q, params).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/chapters")
    def list_chapters():
        with closing(_get_db()) as conn:
            rows = conn.execute("SELECT * FROM chapters ORDER BY chapter ASC").fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/scenes")
    def list_scenes(chapter: int | None = None, limit: int = 500):
        with closing(_get_db()) as conn:
            if chapter is not None:
                rows = conn.execute(
                    "SELECT * FROM scenes WHERE chapter = ? ORDER BY scene_index ASC", (chapter,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM scenes ORDER BY chapter ASC, scene_index ASC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/reading-power")
    def list_reading_power(limit: int = 50):
        with closing(_get_db()) as conn:
            rows = conn.execute(
                "SELECT * FROM chapter_reading_power ORDER BY chapter DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/review-metrics")
    def list_review_metrics(limit: int = 20):
        with closing(_get_db()) as conn:
            rows = conn.execute(
                "SELECT * FROM review_metrics ORDER BY end_chapter DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/state-changes")
    def list_state_changes(entity: str | None = None, limit: int = 100):
        with closing(_get_db()) as conn:
            if entity:
                rows = conn.execute(
                    "SELECT * FROM state_changes WHERE entity_id = ? ORDER BY chapter DESC LIMIT ?",
                    (entity, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM state_changes ORDER BY chapter DESC LIMIT ?", (limit,)
                ).fetchall()
            return [dict(r) for r in rows]

    @app.get("/api/aliases")
    def list_aliases(entity: str | None = None):
        with closing(_get_db()) as conn:
            if entity:
                rows = conn.execute(
                    "SELECT * FROM aliases WHERE entity_id = ?", (entity,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM aliases").fetchall()
            return [dict(r) for r in rows]

    # ===========================================================
    # API：扩展表（v5.3+ / v5.4+）
    # ===========================================================

    @app.get("/api/overrides")
    def list_overrides(status: str | None = None, limit: int = 100):
        with closing(_get_db()) as conn:
            if status:
                return _fetchall_safe(
                    conn,
                    "SELECT * FROM override_contracts WHERE status = ? ORDER BY chapter DESC LIMIT ?",
                    (status, limit),
                )
            return _fetchall_safe(
                conn,
                "SELECT * FROM override_contracts ORDER BY chapter DESC LIMIT ?",
                (limit,),
            )

    @app.get("/api/debts")
    def list_debts(status: str | None = None, limit: int = 100):
        with closing(_get_db()) as conn:
            if status:
                return _fetchall_safe(
                    conn,
                    "SELECT * FROM chase_debt WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status, limit),
                )
            return _fetchall_safe(
                conn,
                "SELECT * FROM chase_debt ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )

    @app.get("/api/debt-events")
    def list_debt_events(debt_id: int | None = None, limit: int = 200):
        with closing(_get_db()) as conn:
            if debt_id is not None:
                return _fetchall_safe(
                    conn,
                    "SELECT * FROM debt_events WHERE debt_id = ? ORDER BY chapter DESC, id DESC LIMIT ?",
                    (debt_id, limit),
                )
            return _fetchall_safe(
                conn,
                "SELECT * FROM debt_events ORDER BY chapter DESC, id DESC LIMIT ?",
                (limit,),
            )

    @app.get("/api/invalid-facts")
    def list_invalid_facts(status: str | None = None, limit: int = 100):
        with closing(_get_db()) as conn:
            if status:
                return _fetchall_safe(
                    conn,
                    "SELECT * FROM invalid_facts WHERE status = ? ORDER BY marked_at DESC LIMIT ?",
                    (status, limit),
                )
            return _fetchall_safe(
                conn,
                "SELECT * FROM invalid_facts ORDER BY marked_at DESC LIMIT ?",
                (limit,),
            )

    @app.get("/api/rag-queries")
    def list_rag_queries(query_type: str | None = None, limit: int = 100):
        with closing(_get_db()) as conn:
            if query_type:
                return _fetchall_safe(
                    conn,
                    "SELECT * FROM rag_query_log WHERE query_type = ? ORDER BY created_at DESC LIMIT ?",
                    (query_type, limit),
                )
            return _fetchall_safe(
                conn,
                "SELECT * FROM rag_query_log ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )

    @app.get("/api/tool-stats")
    def list_tool_stats(tool_name: str | None = None, limit: int = 200):
        with closing(_get_db()) as conn:
            if tool_name:
                return _fetchall_safe(
                    conn,
                    "SELECT * FROM tool_call_stats WHERE tool_name = ? ORDER BY created_at DESC LIMIT ?",
                    (tool_name, limit),
                )
            return _fetchall_safe(
                conn,
                "SELECT * FROM tool_call_stats ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )

    @app.get("/api/checklist-scores")
    def list_checklist_scores(limit: int = 100):
        with closing(_get_db()) as conn:
            return _fetchall_safe(
                conn,
                "SELECT * FROM writing_checklist_scores ORDER BY chapter DESC LIMIT ?",
                (limit,),
            )

    # ===========================================================
    # API：文档浏览（正文/大纲/设定集 —— 只读）
    # ===========================================================

    @app.get("/api/files/tree")
    def file_tree():
        """列出 正文/、大纲/、设定集/ 三个目录的树结构。"""
        root = _get_project_root()
        result = {}
        for folder_name in ("正文", "大纲", "设定集"):
            folder = root / folder_name
            if not folder.is_dir():
                result[folder_name] = []
                continue
            result[folder_name] = _walk_tree(folder, root)
        return result

    @app.get("/api/files/read")
    def file_read(path: str):
        """只读读取一个文件内容（限 正文/大纲/设定集 目录）。"""
        root = _get_project_root()
        resolved = safe_resolve(root, path)

        # 二次限制：只允许三大目录
        allowed_parents = [root / n for n in ("正文", "大纲", "设定集")]
        if not any(_is_child(resolved, p) for p in allowed_parents):
            raise HTTPException(403, "仅允许读取 正文/大纲/设定集 目录下的文件")

        if not resolved.is_file():
            raise HTTPException(404, "文件不存在")

        # 文本文件直接读；其他情况返回占位信息
        try:
            content = resolved.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = "[二进制文件，无法预览]"

        return {"path": path, "content": content}

    @app.post("/api/files/save")
    def file_save(payload: dict):
        path = payload.get("path")
        content = payload.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise HTTPException(400, "path 和 content 必须为字符串")
        return save_workspace_file(_get_project_root(), path, content)

    @app.get("/api/tasks/current")
    def current_task():
        return _task_service.get_current_task()

    @app.post("/api/tasks")
    def create_task(payload: dict):
        action = payload.get("action")
        context = payload.get("context")
        if not isinstance(action, dict):
            raise HTTPException(400, "action 必须为对象")
        if context is not None and not isinstance(context, dict):
            raise HTTPException(400, "context 必须为对象")
        merged_context = {
            **(context or {}),
            "projectRoot": str(_get_project_root()),
        }
        return _task_service.create_task(action, merged_context)

    @app.get("/api/tasks/{task_id}")
    def get_task(task_id: str):
        task = _task_service.get_task(task_id)
        if task is None:
            raise HTTPException(404, "任务不存在")
        return task

    @app.post("/api/chat")
    def chat(payload: dict):
        message = payload.get("message")
        context = payload.get("context")
        if not isinstance(message, str):
            raise HTTPException(400, "message 必须为字符串")
        if context is not None and not isinstance(context, dict):
            raise HTTPException(400, "context 必须为对象")
        return build_chat_response(message, context)

    # ===========================================================
    # Skill API — SkillRunner 生命周期管理（委托至模块级函数）
    # ===========================================================

    @app.post("/api/skill/{skill_name}/start")
    async def _start_skill(skill_name: str, payload: dict):
        result = await start_skill(skill_name, payload)
        from fastapi.responses import JSONResponse
        return JSONResponse(content=result)

    @app.get("/api/skill/pending")
    async def _list_pending_skills(skill_name: str | None = None):
        return await list_pending_skills(skill_name)

    @app.get("/api/skill/{skill_id}/status")
    async def _get_skill_status(skill_id: str):
        return await get_skill_status(skill_id)

    @app.post("/api/skill/{skill_id}/step")
    async def _submit_skill_step(skill_id: str, payload: dict):
        return await submit_skill_step(skill_id, payload)

    @app.post("/api/skill/{skill_id}/cancel")
    async def _cancel_skill(skill_id: str):
        return await cancel_skill(skill_id)

    @app.post("/api/skill/{skill_id}/back")
    async def _go_back_skill(skill_id: str, payload: dict):
        target_step_id = payload.get("step_id", "")
        if not target_step_id:
            raise HTTPException(400, "step_id 必填")
        return await go_back_skill(skill_id, target_step_id)

    @app.get("/api/skill/active")
    async def _list_active_skills():
        return await list_active_skills()

    # ===========================================================
    # API: RAG 配置
    # ===========================================================

    @app.get("/api/rag/config")
    def get_rag_config():
        config = RAGConfig(str(_get_project_root()))
        return {
            "enabled": config.is_rag_enabled(),
            "embedding_model": config.get_embedding_model(),
            "chunk_size": config.get_chunk_size(),
            "chunk_overlap": config.get_chunk_overlap(),
            "has_api_key": config.get_openai_key() is not None,
        }

    @app.post("/api/rag/config")
    def update_rag_config(payload: dict):
        config = RAGConfig(str(_get_project_root()))
        for key, value in payload.items():
            config.set(key, str(value))
        return {"success": True}

    @app.post("/api/rag/test")
    def test_rag_connection():
        """测试 RAG embedding API 连接。"""
        import json as _json
        import urllib.request
        import urllib.error

        config = RAGConfig(str(_get_project_root()))
        api_key = config.get_openai_key()
        if not api_key:
            return {"success": False, "message": "API Key 未配置"}
        model = config.get_embedding_model()
        base_url = config.get("RAG_EMBEDDING_BASE_URL", "https://api.openai.com/v1")

        # 实际调用 embedding API 做轻量级连接测试
        try:
            url = f"{base_url.rstrip('/')}/embeddings"
            payload = _json.dumps({
                "input": "test",
                "model": model,
            }).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                _json.loads(resp.read().decode("utf-8"))
            return {"success": True, "message": f"连接成功（模型: {model}）"}
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if e.code == 401:
                return {"success": False, "message": "API Key 无效或已过期"}
            return {"success": False, "message": f"API 返回错误 {e.code}: {body[:200]}"}
        except urllib.error.URLError as e:
            return {"success": False, "message": f"无法连接到 {base_url}: {e.reason}"}
        except Exception as e:
            return {"success": False, "message": f"测试失败: {str(e)}"}

    # --- RAG 索引构建 API (Task 603) ---

    @app.post("/api/rag/build")
    async def start_rag_build():
        """启动索引构建。"""
        config = RAGConfig(str(_get_project_root()))

        def sse_callback(event_data: dict):
            _emit_rag_event(json.dumps(event_data, ensure_ascii=False))

        return await config.start_build_index(sse_callback=sse_callback)

    @app.get("/api/rag/build/status")
    async def get_rag_build_status(task_id: str = None):
        """查询构建状态。"""
        config = RAGConfig(str(_get_project_root()))
        return config.get_build_status(task_id)

    # ===========================================================
    # SSE: 实时变更推送
    # ===========================================================

    @app.get("/api/events")
    async def sse():
        """Server-Sent Events 端点，推送文件变更、任务状态、Skill 步骤和 RAG 构建进度。"""
        file_q = _watcher.subscribe()
        task_q = _task_service.subscribe_events()
        skill_q = await subscribe_skill_events()
        # RAG 构建事件队列
        rag_q: asyncio.Queue = asyncio.Queue(maxsize=128)
        _rag_subscribers.append(rag_q)

        async def _gen():
            try:
                while True:
                    file_get = asyncio.create_task(file_q.get())
                    task_get = asyncio.create_task(task_q.get())
                    skill_get = asyncio.create_task(skill_q.get())
                    rag_get = asyncio.create_task(rag_q.get())
                    done, pending = await asyncio.wait(
                        {file_get, task_get, skill_get, rag_get},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    for waiter in pending:
                        waiter.cancel()
                    for waiter in done:
                        msg = waiter.result()
                        yield f"data: {msg}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                _watcher.unsubscribe(file_q)
                _task_service.unsubscribe_events(task_q)
                unsubscribe_skill_events(skill_q)
                try:
                    _rag_subscribers.remove(rag_q)
                except ValueError:
                    pass

        return StreamingResponse(_gen(), media_type="text/event-stream")

    # ===========================================================
    # 前端静态文件托管
    # ===========================================================

    if STATIC_DIR.is_dir():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        def serve_spa(full_path: str):
            """SPA fallback：任何非 /api 路径都返回 index.html。"""
            if full_path.startswith("api/"):
                raise HTTPException(404, "API 路由不存在")
            index = STATIC_DIR / "index.html"
            if index.is_file():
                return FileResponse(str(index))
            raise HTTPException(404, "前端尚未构建")
    else:
        @app.get("/")
        def no_frontend():
            return HTMLResponse(
                "<h2>Webnovel Dashboard API is running</h2>"
                "<p>前端尚未构建。请先在 <code>dashboard/frontend</code> 目录执行 <code>npm run build</code>。</p>"
                '<p>API 文档：<a href="/docs">/docs</a></p>'
            )

    return app


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _walk_tree(folder: Path, root: Path) -> list[dict]:
    items = []
    for child in sorted(folder.iterdir()):
        rel = str(child.relative_to(root)).replace("\\", "/")
        if child.is_dir():
            items.append({"name": child.name, "type": "dir", "path": rel, "children": _walk_tree(child, root)})
        else:
            items.append({"name": child.name, "type": "file", "path": rel, "size": child.stat().st_size})
    return items


def _is_child(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
