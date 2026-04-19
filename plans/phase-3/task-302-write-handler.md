# Task 302: WriteSkillHandler 骨架 + 模式选择

## 目标

实现 WriteSkillHandler，定义 6 步章节创作流程的步骤结构，支持 standard/fast/minimal 三种模式。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/write_handler.py`（新建）

## 依赖

- task-301（ScriptAdapter 已扩展）
- Phase 0 已完成：SkillHandler 抽象类、SkillRegistry

## 前置知识

SkillHandler 接口（来自 Phase 0 task-002）：

```python
class SkillHandler(ABC):
    @abstractmethod
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """返回该 Skill 的步骤定义列表。mode 可选。"""

    @abstractmethod
    async def execute_step(self, step: StepState, context: dict) -> dict:
        """执行一个 auto 步骤，返回 output_data。"""

    @abstractmethod
    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """校验 form/confirm 步骤的用户输入。"""
```

StepDefinition 支持 `skippable` 字段，SkillRunner 在执行时会跳过 skippable=True 的步骤。

三种模式的步骤差异：
- standard：Step 1 → 2A → 2B → 3 → 4 → 5 → 6
- fast：Step 1 → 2A → 3 → 4 → 5 → 6（跳过 2B）
- minimal：Step 1 → 2A → 3(仅核心 3 项) → 4 → 5 → 6

## 规格

### WriteSkillHandler

```python
from ..skill_runner import SkillHandler
from ..skill_models import StepDefinition, StepState


class WriteSkillHandler(SkillHandler):
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """根据模式返回步骤列表。

        mode:
            "standard" (默认) — 全部步骤
            "fast" — 跳过 Step 2B（风格适配）
            "minimal" — 跳过 Step 2B，Step 3 仅核心 3 项审查
        """
        mode = mode or "standard"

        steps = [
            StepDefinition(id="step_1", name="Context Agent", interaction="auto"),
            StepDefinition(id="step_2a", name="正文起草", interaction="confirm"),
            StepDefinition(
                id="step_2b", name="风格适配", interaction="confirm",
                skippable=(mode in ("fast", "minimal")),
            ),
            StepDefinition(id="step_3", name="六维审查", interaction="auto"),
            StepDefinition(id="step_4", name="润色", interaction="confirm"),
            StepDefinition(id="step_5", name="Data Agent", interaction="auto"),
            StepDefinition(id="step_6", name="Git 备份", interaction="auto"),
        ]

        return steps

    async def execute_step(self, step: StepState, context: dict) -> dict:
        """执行 auto 步骤。各步骤的具体实现在后续 task 中填充。"""
        if step.step_id == "step_1":
            return {"message": "Context Agent（待实现）"}
        if step.step_id == "step_3":
            return {"message": "六维审查（待实现）"}
        if step.step_id == "step_5":
            return {"message": "Data Agent（待实现）"}
        if step.step_id == "step_6":
            return {"message": "Git 备份（待实现）"}
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """校验 confirm 步骤的用户输入。"""
        if step.step_id == "step_2a":
            return self._validate_draft_confirm(data)
        if step.step_id == "step_2b":
            return self._validate_style_confirm(data)
        if step.step_id == "step_4":
            return self._validate_polish_confirm(data)
        return None

    def _validate_draft_confirm(self, data: dict) -> str | None:
        """Step 2A 确认：用户确认草稿或提交修改。"""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            edited_text = data.get("edited_text", "")
            if not edited_text:
                return "请确认草稿或提交修改后的文本"
        return None

    def _validate_style_confirm(self, data: dict) -> str | None:
        """Step 2B 确认：用户确认风格适配结果。"""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            feedback = data.get("feedback", "")
            if not feedback:
                return "请确认风格适配结果或提出修改意见"
        return None

    def _validate_polish_confirm(self, data: dict) -> str | None:
        """Step 4 确认：用户确认润色结果。"""
        confirmed = data.get("confirmed", False)
        if not confirmed:
            edited_text = data.get("edited_text", "")
            if not edited_text:
                return "请确认润色结果或提交修改后的文本"
        return None
```

### 注册

在 `skill_registry.py` 的 `default_registry` 中注册：

```python
from .skill_handlers.write_handler import WriteSkillHandler
default_registry.register("write", WriteSkillHandler)
```

### 启动参数

前端启动 write Skill 时传入的参数：

```python
# POST /api/skill/write/start 的 body
{
    "project_root": "/path/to/project",
    "chapter_num": 5,           # 要写的章节编号
    "mode": "standard",         # standard / fast / minimal
}
```

SkillRunner 在 start() 时将这些参数存入 context：

```python
context["project_root"] = params["project_root"]
context["chapter_num"] = params["chapter_num"]
context["mode"] = params.get("mode", "standard")
```

## TDD 验收

- Happy path：`get_steps("standard")` → 返回 7 个 StepDefinition → step_2b.skippable == False
- Edge case 1：`get_steps("fast")` → step_2b.skippable == True，其余步骤不变
- Edge case 2：`get_steps("minimal")` → step_2b.skippable == True
- Error case：validate_input("step_2a") 收到 confirmed=False 且无 edited_text → 返回错误信息
