"""Skill data models — StepDefinition, StepState, SkillInstance."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})


def _now_iso() -> str:
    return datetime.now().isoformat()


@dataclass
class StepDefinition:
    id: str
    name: str
    interaction: str  # "auto" | "form" | "confirm"
    skippable: bool = False
    schema: dict | None = None  # form 步骤的表单定义

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> StepDefinition:
        return cls(
            id=data["id"],
            name=data["name"],
            interaction=data["interaction"],
            skippable=data.get("skippable", False),
            schema=data.get("schema"),
        )


@dataclass
class StepState:
    step_id: str
    status: str  # "pending" | "waiting_input" | "running" | "done" | "failed" | "skipped"
    started_at: str | None = None
    completed_at: str | None = None
    input_data: dict | None = None
    output_data: dict | None = None
    error: str | None = None
    progress: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> StepState:
        return cls(
            step_id=data["step_id"],
            status=data["status"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            input_data=data.get("input_data"),
            output_data=data.get("output_data"),
            error=data.get("error"),
            progress=data.get("progress", 0.0),
        )


@dataclass
class SkillInstance:
    id: str
    skill_name: str  # "init" | "plan" | "write" | "review" | "query"
    status: str  # "created" | "running" | "completed" | "failed" | "cancelled"
    project_root: str = ""
    steps: list[StepDefinition] = field(default_factory=list)
    step_states: list[StepState] = field(default_factory=list)
    current_step_index: int = 0
    mode: str | None = None  # "standard" | "fast" | "minimal" (write 专用)
    created_at: str = ""
    updated_at: str = ""
    context: dict = field(default_factory=dict)
    display_name: str = ""  # 中文显示名

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "display_name": self.display_name,
            "status": self.status,
            "mode": self.mode,
            "project_root": self.project_root,
            "steps": [s.to_dict() for s in self.steps],
            "step_states": [s.to_dict() for s in self.step_states],
            "current_step_index": self.current_step_index,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SkillInstance:
        if not isinstance(data, dict):
            raise TypeError("from_dict requires a dict")
        _require(data, "id")
        _require(data, "skill_name")
        _require(data, "status")
        return cls(
            id=data["id"],
            skill_name=data["skill_name"],
            display_name=data.get("display_name", ""),
            status=data["status"],
            mode=data.get("mode"),
            project_root=data.get("project_root", ""),
            steps=[StepDefinition.from_dict(s) for s in data.get("steps", [])],
            step_states=[StepState.from_dict(s) for s in data.get("step_states", [])],
            current_step_index=data.get("current_step_index", 0),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            context=data.get("context", {}),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def current_step(self) -> StepState | None:
        """Return the current StepState, or None if step_states is empty."""
        if not self.step_states:
            return None
        return self.step_states[self.current_step_index]

    def advance(self) -> bool:
        """Move current_step_index forward. Returns False when already at the end.

        Sets the newly-current step state to ``pending`` (auto steps are executed
        immediately by SkillRunner) or ``waiting_input`` (form/confirm steps wait
        for user input).
        """
        if not self.step_states:
            return False
        if self.current_step_index >= len(self.step_states) - 1:
            return False
        self.current_step_index += 1
        if self.step_states:
            step_id = self.step_states[self.current_step_index].step_id
            step_def = next((s for s in self.steps if s.id == step_id), None)
            if step_def and step_def.interaction in ("form", "confirm"):
                self.step_states[self.current_step_index].status = "waiting_input"
            else:
                self.step_states[self.current_step_index].status = "pending"
        return True

    def go_back(self, target_index: int) -> None:
        """Reset to a previous step, keeping input_data intact.

        Sets all steps after target_index back to pending,
        and sets the target step to waiting_input.
        """
        if target_index < 0 or target_index >= len(self.step_states):
            return
        if target_index >= self.current_step_index:
            return
        # Reset steps after target to pending
        for i in range(target_index + 1, len(self.step_states)):
            self.step_states[i].status = "pending"
            self.step_states[i].output_data = None
            self.step_states[i].error = None
            self.step_states[i].progress = 0.0
        # Set target step back to waiting_input
        self.step_states[target_index].status = "waiting_input"
        self.step_states[target_index].output_data = None
        self.step_states[target_index].error = None
        self.current_step_index = target_index
        self.updated_at = _now_iso()

    def is_terminal(self) -> bool:
        """Return True when status is completed / failed / cancelled."""
        return self.status in TERMINAL_STATUSES


def _require(data: dict, key: str) -> None:
    """Raise KeyError if key is absent from data."""
    if key not in data:
        raise KeyError(key)
