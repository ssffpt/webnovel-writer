"""SkillRunner — state machine that drives SkillInstance lifecycle.

Implements the execution loop described in Task 002.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from dashboard.skill_models import SkillInstance

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SkillHandler abstract interface
# ---------------------------------------------------------------------------


class SkillHandler(ABC):
    """Abstract interface implemented by each Skill (init, plan, write, …)."""

    @abstractmethod
    def get_steps(self, mode: str | None = None) -> list:
        """Return the list of StepDefinition for this Skill.

        Args:
            mode: Skill-specific mode such as "standard" | "fast" | "minimal"
                  (used by the write skill).

        Returns:
            List of StepDefinition dataclass instances.
        """

    @abstractmethod
    async def execute_step(self, step, context: dict) -> dict:
        """Execute one auto step; return its output_data dict."""

    @abstractmethod
    async def validate_input(self, step, data: dict) -> str | None:
        """Validate user input for a form / confirm step.

        Args:
            step: The StepState that is waiting for input.
            data: The raw form / confirm payload submitted by the user.

        Returns:
            None if validation passes; an error message string otherwise.
        """


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now().isoformat()


def _persist_instance(instance: "SkillInstance") -> None:
    """Write instance.to_dict() to .webnovel/workflow/instances/{id}.json."""
    project_root = Path(instance.project_root)
    if not str(project_root) or not project_root.is_dir():
        return
    instances_dir = project_root / ".webnovel" / "workflow" / "instances"
    try:
        instances_dir.mkdir(parents=True, exist_ok=True)
        path = instances_dir / f"{instance.id}.json"
        path.write_text(json.dumps(instance.to_dict(), ensure_ascii=False), encoding="utf-8")
    except OSError as exc:
        logger.warning("failed to persist SkillInstance %s: %s", instance.id, exc)


def _notify_step_change(
    callback: Callable[["SkillInstance", object], None] | None,
    instance: "SkillInstance",
    step: object,
) -> None:
    if callback is not None:
        try:
            callback(instance, step)
        except Exception as exc:
            logger.warning("on_step_change callback raised: %s", exc)


def _call_workflow_manager(
    action: str,
    instance: "SkillInstance",
    step_name: str | None = None,
    step_id: str | None = None,
) -> None:
    """Dual-write to workflow_state.json (best-effort, never raises).

    Directly writes to the same JSON file that scripts/workflow_manager.py uses,
    providing CLI-compatible interruption recovery without subprocess overhead.
    """
    try:
        project_root = Path(instance.project_root)
        if not str(project_root) or not project_root.is_dir():
            return

        state_file = project_root / ".webnovel" / "workflow_state.json"

        # Load or initialise state
        if state_file.exists():
            state = json.loads(state_file.read_text(encoding="utf-8"))
        else:
            state = {"current_task": None, "last_stable_state": None, "history": []}

        task = state.get("current_task")

        if action == "start-task":
            started_at = _now_iso()
            state["current_task"] = {
                "command": f"webnovel-{instance.skill_name}",
                "args": {},
                "started_at": started_at,
                "last_heartbeat": started_at,
                "status": "running",
                "current_step": None,
                "completed_steps": [],
                "failed_steps": [],
                "pending_steps": [],
                "retry_count": 0,
                "artifacts": {},
            }
            _atomic_write_json(state_file, state)

        elif action == "complete-task":
            if task:
                task["status"] = "completed"
                task["completed_at"] = _now_iso()
                state["last_stable_state"] = {
                    "command": task.get("command"),
                    "chapter_num": task.get("args", {}).get("chapter_num"),
                    "completed_at": task.get("completed_at"),
                    "artifacts": task.get("artifacts", {}),
                }
                state["current_task"] = None
                _atomic_write_json(state_file, state)

        elif action == "start-step":
            if task and step_id:
                task["current_step"] = {
                    "id": step_id,
                    "name": step_name or step_id,
                    "status": "running",
                    "started_at": _now_iso(),
                    "running_at": _now_iso(),
                    "attempt": 1,
                    "progress_note": None,
                }
                task["status"] = "running"
                task["last_heartbeat"] = _now_iso()
                _atomic_write_json(state_file, state)

        elif action == "complete-step":
            if task and step_id:
                cs = task.get("current_step")
                if cs and cs.get("id") == step_id:
                    cs["status"] = "completed"
                    cs["completed_at"] = _now_iso()
                    task.setdefault("completed_steps", []).append(cs)
                    task["current_step"] = None
                    task["last_heartbeat"] = _now_iso()
                    _atomic_write_json(state_file, state)

    except Exception as exc:
        logger.debug("workflow_manager dual-write skipped: %s", exc)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically (write-then-rename)."""
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.rename(path)


# ---------------------------------------------------------------------------
# SkillRunner
# ---------------------------------------------------------------------------


class SkillRunner:
    """Drives a SkillInstance through its step lifecycle.

    Parameters
    ----------
    instance:
        The SkillInstance to run.  Must be in "created" status on construction.
    handler:
        The SkillHandler that knows how to execute each step.
    on_step_change:
        Optional callback ``(instance, step_state) -> None`` called whenever a
        step's status changes.  Used by the SSE push layer (task-005).
    """

    def __init__(
        self,
        instance: "SkillInstance",
        handler: SkillHandler,
        on_step_change: Callable[["SkillInstance", object], None] | None = None,
    ) -> None:
        self.instance = instance
        self.handler = handler
        self.on_step_change = on_step_change
        self._started = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Begin executing the skill.

        - Sets instance.status to "running".
        - auto steps execute immediately and the loop continues.
        - form / confirm steps set to ``waiting_input`` and stop.
        - Raises RuntimeError if called on a terminal or already-started instance.
        """
        if self.instance.is_terminal():
            raise RuntimeError(
                f"SkillRunner.start() called on a terminal instance (status={self.instance.status})"
            )
        # Allow re-entry when resuming a running instance (via SkillRunner.resume()).
        # Raise only on a genuine second call to a fresh start().
        if self._started and self.instance.status == "running":
            raise RuntimeError(
                f"SkillRunner.start() called twice (current status={self.instance.status})"
            )
        if not self._started:
            self.instance.status = "running"
            self.instance.updated_at = _now_iso()
            _persist_instance(self.instance)
            _call_workflow_manager("start-task", self.instance)
            self._started = True

        # On resume, auto steps may be stuck in "waiting_input" — reset them to
        # "pending" so the loop can execute them.
        current = self.instance.current_step()
        if current is not None and current.status == "waiting_input":
            step_def = next(
                (s for s in self.instance.steps if s.id == current.step_id), None,
            )
            if step_def is None or step_def.interaction == "auto":
                current.status = "pending"

        # Run steps in a loop: keep going while we hit auto steps.
        while True:
            current = self.instance.current_step()
            if current is None:
                # No steps at all — complete immediately
                self.instance.status = "completed"
                self.instance.updated_at = _now_iso()
                _persist_instance(self.instance)
                _notify_step_change(self.on_step_change, self.instance, None)
                _call_workflow_manager("complete-task", self.instance)
                return

            step_def = next(
                (s for s in self.instance.steps if s.id == current.step_id), None,
            )
            interaction = step_def.interaction if step_def else "auto"

            if interaction == "confirm":
                # Pre-execute confirm step so frontend can see output_data (e.g. packages)
                try:
                    output_data = await self.handler.execute_step(current, self.instance.context)
                    current.output_data = output_data
                except Exception as exc:
                    logger.warning("pre-execute for confirm step %s failed: %s", current.step_id, exc)
                current.status = "waiting_input"
                current.started_at = _now_iso()
                self.instance.updated_at = _now_iso()
                _persist_instance(self.instance)
                _notify_step_change(self.on_step_change, self.instance, current)
                return

            if interaction == "form":
                # Wait for user input; stop here.
                current.status = "waiting_input"
                current.started_at = _now_iso()
                self.instance.updated_at = _now_iso()
                _persist_instance(self.instance)
                _notify_step_change(self.on_step_change, self.instance, current)
                return

            # auto: execute it
            ok = await self._execute_auto_step(current)
            if not ok:
                # Error already recorded; instance is "failed"
                return

            # Advance or complete
            if not self.instance.advance():
                self.instance.status = "completed"
                self.instance.updated_at = _now_iso()
                _persist_instance(self.instance)
                _notify_step_change(
                    self.on_step_change, self.instance, self.instance.current_step(),
                )
                _call_workflow_manager("complete-task", self.instance)
                return

            _persist_instance(self.instance)
            _notify_step_change(
                self.on_step_change, self.instance, self.instance.current_step(),
            )

    async def submit_input(self, step_id: str, data: dict) -> None:
        """Submit user input for a waiting ``form`` / ``confirm`` step.

        Parameters
        ----------
        step_id:
            The step being answered. Must match the currently-waiting step.
        data:
            The form / confirm payload.

        Raises
        ------
        ValueError
            If ``step_id`` does not match the current step.
        RuntimeError
            If the instance is not ``running``.
        """
        if self.instance.status == "cancelled":
            return  # No-op after cancel
        if self.instance.is_terminal():
            raise RuntimeError(
                f"submit_input called on a terminal instance (status={self.instance.status})"
            )

        current = self.instance.current_step()
        if current is None or current.step_id != step_id:
            raise ValueError(
                f"submit_input received step_id '{step_id}' but current step is "
                f"'{current.step_id if current else None}'"
            )

        # Validate
        error_msg = await self.handler.validate_input(current, data)
        if error_msg is not None:
            # Validation failed — step stays waiting_input; caller surfaces the error.
            return

        # Execute the step
        current.input_data = data
        current.status = "running"
        current.started_at = _now_iso()
        self.instance.updated_at = _now_iso()
        _persist_instance(self.instance)
        _notify_step_change(self.on_step_change, self.instance, current)

        step_def = next((s for s in self.instance.steps if s.id == step_id), None)
        step_name = step_def.name if step_def else step_id
        _call_workflow_manager(
            "start-step", self.instance, step_name=step_name, step_id=step_id,
        )

        # For confirm steps, execute_step was already called during start() (pre-execute).
        # We need to re-execute to process the user's selection.
        # Also merge input_data into context so handlers can access it.
        if step_def and step_def.interaction == "confirm":
            self.instance.context.update(data)
            current.output_data = None

        try:
            output_data = await self.handler.execute_step(current, self.instance.context)
            current.output_data = output_data
            current.status = "done"
            current.completed_at = _now_iso()
            current.progress = 1.0
            self.instance.updated_at = _now_iso()
            _persist_instance(self.instance)
            _notify_step_change(self.on_step_change, self.instance, current)
            _call_workflow_manager("complete-step", self.instance, step_id=step_id)
        except Exception as exc:
            current.status = "failed"
            current.error = f"{type(exc).__name__}: {exc}"
            current.completed_at = _now_iso()
            self.instance.status = "failed"
            self.instance.updated_at = _now_iso()
            _persist_instance(self.instance)
            _notify_step_change(self.on_step_change, self.instance, current)
            return

        # Advance and keep looping through any remaining auto steps.
        while True:
            if not self.instance.advance():
                self.instance.status = "completed"
                self.instance.updated_at = _now_iso()
                _persist_instance(self.instance)
                _notify_step_change(
                    self.on_step_change, self.instance, self.instance.current_step(),
                )
                _call_workflow_manager("complete-task", self.instance)
                return

            _persist_instance(self.instance)
            _notify_step_change(
                self.on_step_change, self.instance, self.instance.current_step(),
            )

            next_step = self.instance.current_step()
            next_def = next(
                (s for s in self.instance.steps if s.id == next_step.step_id), None,
            )
            if next_def and next_def.interaction == "confirm":
                # Pre-execute confirm step so frontend can see output_data
                try:
                    output_data = await self.handler.execute_step(next_step, self.instance.context)
                    next_step.output_data = output_data
                except Exception as exc:
                    logger.warning("pre-execute for confirm step %s failed: %s", next_step.step_id, exc)
                next_step.status = "waiting_input"
                next_step.started_at = _now_iso()
                self.instance.updated_at = _now_iso()
                _persist_instance(self.instance)
                _notify_step_change(self.on_step_change, self.instance, next_step)
                return

            if next_def and next_def.interaction == "form":
                # Stop here and wait for more user input.
                return

            # auto: execute it
            ok = await self._execute_auto_step(next_step)
            if not ok:
                return

    async def cancel(self) -> None:
        """Cancel the running skill."""
        self.instance.status = "cancelled"
        self.instance.updated_at = _now_iso()
        _persist_instance(self.instance)

    async def go_back(self, target_step_id: str) -> None:
        """Go back to a previous step, preserving its input_data.

        Resets all steps after the target to pending and sets the target
        step to waiting_input so the user can re-edit and re-submit.
        """
        if self.instance.is_terminal():
            return
        # Find target index
        target_index = None
        for i, ss in enumerate(self.instance.step_states):
            if ss.step_id == target_step_id:
                target_index = i
                break
        if target_index is None:
            return
        # Also need to re-merge context: remove input_data from steps after target
        # so that re-submission starts clean from the target step
        for i in range(target_index + 1, len(self.instance.step_states)):
            ss = self.instance.step_states[i]
            if ss.input_data:
                # Remove these keys from context if they were merged
                for key in ss.input_data:
                    self.instance.context.pop(key, None)
        self.instance.go_back(target_index)
        _persist_instance(self.instance)
        _notify_step_change(self.on_step_change, self.instance, self.instance.current_step())

    def get_state(self) -> dict:
        """Return the full SkillInstance serialised as a plain dict (for API responses)."""
        return self.instance.to_dict()

    # ------------------------------------------------------------------
    # Resume
    # ------------------------------------------------------------------

    @classmethod
    async def resume(cls, path: Path, handler: SkillHandler) -> "SkillRunner":
        """Restore a SkillRunner from a JSON file written by _persist_instance.

        The restored runner is ready for ``submit_input()`` (waiting_input step) or
        ``start()`` (auto steps that need to resume).

        Parameters
        ----------
        path:
            Path to the JSON file in ``.webnovel/workflow/instances/``.
        handler:
            The SkillHandler to use for step execution.

        Returns
        -------
        SkillRunner

        Raises
        ------
        FileNotFoundError
            If ``path`` does not exist.
        """
        if not path.exists():
            raise FileNotFoundError(f"SkillRunner.resume() cannot find: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        from dashboard.skill_models import SkillInstance

        instance = SkillInstance.from_dict(data)
        return cls(instance=instance, handler=handler)

    # ------------------------------------------------------------------
    # Internal: execute one auto step
    # ------------------------------------------------------------------

    async def _execute_auto_step(self, step) -> bool:
        """Execute a single auto step. Returns True on success, False on failure."""
        step.status = "running"
        step.started_at = _now_iso()
        self.instance.updated_at = _now_iso()
        _persist_instance(self.instance)
        _notify_step_change(self.on_step_change, self.instance, step)

        step_def = next(
            (s for s in self.instance.steps if s.id == step.step_id), None,
        )
        step_name = step_def.name if step_def else step.step_id
        _call_workflow_manager(
            "start-step", self.instance, step_name=step_name, step_id=step.step_id,
        )

        try:
            output_data = await self.handler.execute_step(step, self.instance.context)
            step.output_data = output_data
            step.status = "done"
            step.completed_at = _now_iso()
            step.progress = 1.0
            self.instance.updated_at = _now_iso()
            _persist_instance(self.instance)
            _notify_step_change(self.on_step_change, self.instance, step)
            _call_workflow_manager("complete-step", self.instance, step_id=step.step_id)
            return True
        except Exception as exc:
            step.status = "failed"
            step.error = f"{type(exc).__name__}: {exc}"
            step.completed_at = _now_iso()
            self.instance.status = "failed"
            self.instance.updated_at = _now_iso()
            _persist_instance(self.instance)
            _notify_step_change(self.on_step_change, self.instance, step)
            return False
