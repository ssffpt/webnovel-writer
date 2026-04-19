# Task 004: Skill API 端点

## 目标

在 FastAPI 中添加 Skill 相关的 HTTP 端点，前端可以启动/查询/提交输入/取消 Skill 流程。

## 涉及文件

- `webnovel-writer/dashboard/app.py`（修改，添加路由）

## 依赖

- task-003（SkillRegistry + EchoSkillHandler）

## 规格

### 新增端点

```
POST /api/skill/{skill_name}/start
  Body: { "mode": "standard"|null, "context": {} }
  Response: { "id": "xxx", "status": "running", "steps": [...], "current_step_index": 0 }

GET  /api/skill/{skill_id}/status
  Response: SkillInstance.to_dict()

POST /api/skill/{skill_id}/step
  Body: { "step_id": "step_2", "data": { ... } }
  Response: SkillInstance.to_dict()

POST /api/skill/{skill_id}/cancel
  Response: { "id": "xxx", "status": "cancelled" }

GET  /api/skill/active
  Response: { "instances": [ ... ] }  # 当前活跃的 Skill 实例列表
```

### 实现要点

- 用 dict 存储活跃的 SkillRunner 实例（`_active_skills: dict[str, SkillRunner]`）
- `start` 端点：从 registry 获取 handler → 创建 SkillInstance → 创建 SkillRunner → 调用 start()
- `step` 端点：从 _active_skills 获取 runner → 调用 submit_input()
- `cancel` 端点：调用 runner.cancel()
- SkillRunner.start() 是 async 的，需要用 `asyncio.create_task()` 在后台执行
- 错误处理：skill_id 不存在 → 404，skill_name 未注册 → 400

### 不做的事

- 不在此 task 实现 SSE 推送（task-005）
- 不在此 task 实现前端（task-006）

## TDD 验收

- Happy path：POST /api/skill/echo/start → 200 → GET status → 看到步骤在推进
- Edge case 1：POST /api/skill/不存在/start → 400
- Edge case 2：POST /api/skill/{id}/step 提交 form 数据 → 流程继续
- Error case：GET /api/skill/不存在的id/status → 404
