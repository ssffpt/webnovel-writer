# Task 001: Skill 数据模型

## 目标

定义 Skill 流程的核心数据结构：SkillInstance、StepDefinition、StepState。

## 涉及文件

- `webnovel-writer/dashboard/skill_models.py`（新建）

## 输入

无依赖。

## 规格

### SkillInstance

```python
@dataclass
class StepDefinition:
    id: str                    # "step_1", "step_2" 等
    name: str                  # "加载项目数据"
    interaction: str           # "auto" | "form" | "confirm"
    skippable: bool = False    # 该模式下是否可跳过

@dataclass
class StepState:
    step_id: str
    status: str                # "pending" | "waiting_input" | "running" | "done" | "failed" | "skipped"
    started_at: str | None = None
    completed_at: str | None = None
    input_data: dict | None = None    # 用户提交的表单数据
    output_data: dict | None = None   # 该步骤的产出
    error: str | None = None
    progress: float = 0.0             # 0.0 ~ 1.0

@dataclass
class SkillInstance:
    id: str                    # uuid
    skill_name: str            # "init" | "plan" | "write" | "review" | "query"
    status: str                # "created" | "running" | "completed" | "failed" | "cancelled"
    mode: str | None = None    # "standard" | "fast" | "minimal"（write 专用）
    project_root: str = ""
    steps: list[StepDefinition]       # 该 Skill 的步骤定义
    step_states: list[StepState]      # 每步的运行时状态
    current_step_index: int = 0
    created_at: str = ""
    updated_at: str = ""
    context: dict = field(default_factory=dict)  # 跨步骤共享的上下文
```

### 序列化

- `to_dict()` → 可 JSON 序列化的 dict（用于 API 响应和持久化）
- `from_dict(data)` → 从 dict 恢复（用于断点恢复）

### 辅助方法

- `current_step() -> StepState | None`：返回当前步骤状态
- `advance() -> bool`：推进到下一步，返回是否还有后续步骤
- `is_terminal() -> bool`：是否已结束（completed/failed/cancelled）

## TDD 验收

- Happy path：创建 SkillInstance → 序列化 → 反序列化 → 字段一致
- Edge case 1：advance() 到最后一步后返回 False
- Edge case 2：is_terminal() 在各状态下的返回值
- Error case：from_dict() 传入缺失字段时抛出明确异常
