# Task 101: InitSkillHandler 骨架

## 目标

实现 InitSkillHandler，定义 6 步初始化流程的步骤结构，注册到 SkillRegistry。

## 涉及文件

- `webnovel-writer/dashboard/skill_handlers/init_handler.py`（新建）

## 依赖

- Phase 0 已完成：SkillHandler 抽象类在 `skill_runner.py`，SkillRegistry 在 `skill_registry.py`

## 前置知识

SkillHandler 接口（来自 Phase 0 task-002）：

```python
from abc import ABC, abstractmethod
from .skill_models import StepDefinition, StepState

class SkillHandler(ABC):
    @abstractmethod
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        """返回该 Skill 的步骤定义列表。"""

    @abstractmethod
    async def execute_step(self, step: StepState, context: dict) -> dict:
        """执行一个 auto 步骤，返回 output_data。"""

    @abstractmethod
    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """校验 form/confirm 步骤的用户输入，返回 None 表示通过，否则返回错误信息。"""
```

StepDefinition（来自 Phase 0 task-001）：

```python
@dataclass
class StepDefinition:
    id: str                    # "step_1", "step_2" 等
    name: str                  # "故事核与商业定位"
    interaction: str           # "auto" | "form" | "confirm"
    skippable: bool = False
```

## 规格

### InitSkillHandler

```python
class InitSkillHandler(SkillHandler):
    def get_steps(self, mode: str | None = None) -> list[StepDefinition]:
        return [
            StepDefinition(id="step_1", name="故事核与商业定位", interaction="form"),
            StepDefinition(id="step_2", name="角色骨架与关系冲突", interaction="form"),
            StepDefinition(id="step_3", name="金手指与兑现机制", interaction="form"),
            StepDefinition(id="step_4", name="世界观与力量规则", interaction="form"),
            StepDefinition(id="step_5", name="创意约束包", interaction="confirm"),
            StepDefinition(id="step_6", name="一致性复述与确认", interaction="confirm"),
        ]

    async def execute_step(self, step: StepState, context: dict) -> dict:
        """Step 5 和 Step 6 的 auto 部分（生成创意包/摘要）。"""
        # 本 task 只实现骨架，具体逻辑在 task-103/104 中填充
        if step.step_id == "step_5":
            return {"message": "创意约束包生成（待实现）", "packages": []}
        if step.step_6 == "step_6":
            return {"message": "一致性复述（待实现）", "summary": ""}
        return {}

    async def validate_input(self, step: StepState, data: dict) -> str | None:
        """校验各步表单输入。本 task 只实现骨架，具体校验在 task-102 中填充。"""
        return None
```

### 注册

在 `skill_registry.py` 的 `default_registry` 中注册：

```python
from .skill_handlers.init_handler import InitSkillHandler
default_registry.register("init", InitSkillHandler)
```

### 目录结构

```
webnovel-writer/dashboard/
  skill_handlers/
    __init__.py
    init_handler.py
```

## TDD 验收

- Happy path：`default_registry.get_handler("init")` → 返回 InitSkillHandler 实例 → `get_steps()` 返回 6 个 StepDefinition
- Edge case 1：每个 step 的 interaction 类型正确（前 4 个 form，后 2 个 confirm）
- Edge case 2：`validate_input()` 骨架对任意输入返回 None（不阻断）
- Error case：`execute_step()` 对未知 step_id 返回空 dict 而非抛异常
