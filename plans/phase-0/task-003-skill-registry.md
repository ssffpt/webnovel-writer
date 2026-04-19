# Task 003: SkillRegistry + Echo 测试 Skill

## 目标

实现 SkillRegistry（Skill Handler 注册表）和一个 echo 测试 Skill，用于验证整条管道。

## 涉及文件

- `webnovel-writer/dashboard/skill_registry.py`（新建）

## 依赖

- task-002（SkillRunner, SkillHandler）

## 规格

### SkillRegistry

```python
class SkillRegistry:
    def register(self, name: str, handler_factory: Callable[[], SkillHandler]) -> None:
        """注册一个 Skill Handler 工厂函数。"""

    def get_handler(self, name: str) -> SkillHandler:
        """获取 Skill Handler 实例。KeyError if not found。"""

    def list_skills(self) -> list[str]:
        """返回已注册的 Skill 名称列表。"""
```

### EchoSkillHandler

一个用于测试的 Skill，3 个步骤：

| Step | 名称 | interaction | 行为 |
|------|------|------------|------|
| step_1 | 准备 | auto | sleep 0.1s，返回 `{"message": "准备完成"}` |
| step_2 | 用户确认 | confirm | 等待用户提交，返回用户输入 |
| step_3 | 完成 | auto | sleep 0.1s，返回 `{"message": "echo 完成", "echo": context}` |

### 默认注册

模块加载时自动注册 echo Skill：

```python
default_registry = SkillRegistry()
default_registry.register("echo", EchoSkillHandler)
```

## TDD 验收

- Happy path：registry.get_handler("echo") → 创建 SkillRunner → start() → submit_input("step_2", {"ok": True}) → 走完
- Edge case 1：registry.get_handler("不存在") → KeyError
- Edge case 2：list_skills() 返回 ["echo"]
- Error case：EchoSkillHandler.validate_input() 对空 data 返回错误信息
