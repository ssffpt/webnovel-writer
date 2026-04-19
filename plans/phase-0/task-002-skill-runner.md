# Task 002: SkillRunner 状态机

## 目标

实现 SkillRunner，驱动 SkillInstance 的生命周期：启动 → 逐步执行 → 完成/失败。

## 涉及文件

- `webnovel-writer/dashboard/skill_runner.py`（新建）

## 依赖

- task-001（SkillInstance, StepState 等数据模型）

## 规格

### SkillRunner

```python
class SkillRunner:
    def __init__(self, instance: SkillInstance, handler: SkillHandler):
        ...

    async def start(self) -> None:
        """启动 Skill，开始执行第一个 auto 步骤或等待第一个 form 步骤的输入。"""

    async def submit_input(self, step_id: str, data: dict) -> None:
        """用户提交 form/confirm 步骤的输入，继续执行。"""

    async def cancel(self) -> None:
        """取消当前 Skill。"""

    def get_state(self) -> dict:
        """返回当前 SkillInstance 的完整状态（用于 API 响应）。"""
```

### SkillHandler（抽象接口）

```python
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

### 执行逻辑

1. `start()` 时，将 instance.status 设为 "running"
2. 检查当前步骤的 interaction 类型：
   - `auto`：立即调用 `handler.execute_step()`，完成后自动 advance
   - `form` / `confirm`：将步骤状态设为 `waiting_input`，等待 `submit_input()`
3. `submit_input()` 时，先调用 `handler.validate_input()`，通过后执行步骤，然后 advance
4. 所有步骤完成后，instance.status 设为 "completed"
5. 任何步骤失败，instance.status 设为 "failed"，记录 error

### 事件回调

```python
# SkillRunner 构造时接受可选的事件回调
on_step_change: Callable[[SkillInstance, StepState], None] | None
```

每次步骤状态变化时调用，用于 SSE 推送（task-005 接入）。

### 状态持久化

- 每次步骤状态变化后，将 `instance.to_dict()` 写入 `.webnovel/workflow/instances/{skill_id}.json`
- 同时调用 `workflow_manager.py` 的 `start-task` / `complete-step` 双写 `workflow_state.json`（兼容 CLI resume，best-effort，失败不阻断）
- `SkillRunner.resume(path)` 类方法：从 JSON 文件恢复 SkillRunner，继续执行剩余步骤

## TDD 验收

- Happy path：3 步全 auto 的 Skill → start() → 自动走完 → status == "completed"
- Edge case 1：中间有 form 步骤 → start() 停在 waiting_input → submit_input() 后继续
- Edge case 2：resume() 从 JSON 恢复后继续执行剩余步骤
- Error case：execute_step() 抛异常 → 步骤 status == "failed"，instance status == "failed"
