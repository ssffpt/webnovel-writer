"""SkillRegistry — registry of SkillHandler factories."""
from __future__ import annotations

from dashboard.skill_handlers import (
    EchoSkillHandler,
    InitSkillHandler,
    PlanSkillHandler,
    ReviewSkillHandler,
    WriteSkillHandler,
)
from dashboard.skill_runner import SkillHandler


class SkillRegistry:
    """Registry for SkillHandler classes.

    Provides registration, lookup, and listing of available Skills.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, type[SkillHandler]] = {}
        self._display_names: dict[str, str] = {}

    def register(self, name: str, handler_cls: type[SkillHandler], display_name: str | None = None) -> None:
        """Register a Skill Handler class under the given name."""
        self._handlers[name] = handler_cls
        if display_name:
            self._display_names[name] = display_name

    def get_handler(self, name: str) -> SkillHandler:
        """Instantiate and return the handler for the given skill name.

        Raises
        ------
        KeyError
            If no handler is registered under ``name``.
        """
        if name not in self._handlers:
            raise KeyError(f"no handler registered for skill: {name}")
        return self._handlers[name]()

    def get_display_name(self, name: str) -> str:
        """Return the display name for a skill, falling back to the raw name."""
        return self._display_names.get(name, name)

    def list_skills(self) -> list[str]:
        """Return the list of registered skill names."""
        return list(self._handlers.keys())


# Module-level default registry with echo and init already registered.
default_registry = SkillRegistry()
default_registry.register("echo", EchoSkillHandler, "回声测试")
default_registry.register("init", InitSkillHandler, "项目初始化")
default_registry.register("plan", PlanSkillHandler, "大纲规划")
default_registry.register("write", WriteSkillHandler, "章节写作")
default_registry.register("review", ReviewSkillHandler, "审查修订")
