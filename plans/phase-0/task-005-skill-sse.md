# Task 005: SSE Skill 事件推送

## 目标

将 Skill 步骤状态变化通过 SSE 实时推送到前端。

## 涉及文件

- `webnovel-writer/dashboard/skill_runner.py`（修改，接入事件回调）
- `webnovel-writer/dashboard/app.py`（修改，SSE 端点扩展）

## 依赖

- task-004（Skill API 端点已就绪）

## 规格

### SSE 事件格式

复用现有 `/api/events` SSE 端点，新增事件类型：

```json
{
  "type": "skill.step",
  "skillId": "xxx",
  "skillName": "echo",
  "step": {
    "id": "step_1",
    "name": "准备",
    "status": "running",
    "progress": 0.5
  }
}
```

```json
{
  "type": "skill.completed",
  "skillId": "xxx",
  "skillName": "echo"
}
```

```json
{
  "type": "skill.failed",
  "skillId": "xxx",
  "skillName": "echo",
  "error": "xxx"
}
```

### 实现要点

- 在 app.py 的 `start` 端点中，创建 SkillRunner 时传入 `on_step_change` 回调
- 回调函数将事件 JSON 放入现有 `_task_service` 的事件队列（或新建一个 skill 专用队列）
- SSE 端点 `/api/events` 已有 `task_q`，新增 `skill_q` 并在 `_gen()` 中同时监听
- 日志消息也通过 SSE 推送：`{ "type": "skill.log", "skillId": "xxx", "message": "..." }`

### 不做的事

- 不在此 task 实现前端消费（task-006）

## TDD 验收

- Happy path：启动 echo skill → 监听 SSE → 收到 skill.step 事件序列 → 最终收到 skill.completed
- Edge case 1：skill 失败时收到 skill.failed 事件
- Error case：SSE 连接断开后重连，能收到后续事件
