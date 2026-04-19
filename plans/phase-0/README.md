# Phase 0: SkillRunner 基础设施

## 目标

替代当前的 `claude_runner.py`（半真实命令映射），实现完整的 Skill 生命周期管理。
Phase 0 完成后，后端具备"启动一个多步骤 Skill → 逐步执行 → SSE 推送进度 → 前端展示 → 断点恢复"的端到端能力。

## 架构决策

- SkillRunner 是纯 Python 状态机，不依赖 AI API（AI 调用在各 Phase 的具体 Skill Handler 中实现）
- Phase 0 用一个 `echo` 测试 Skill 验证管道通畅，不接入真实 CLI 流程
- 状态持久化到 `.webnovel/workflow/instances/` 目录（每实例一个 JSON），同时双写 `workflow_state.json` 兼容 CLI
- 复用现有 `TaskService` 的 SSE 基础设施，扩展事件类型（`/api/tasks` 与 `/api/skill/*` 双轨并存）
- scripts/ 调用通过 ScriptAdapter 封装（Phase 0 仅定义接口，echo Skill 不需要调用 scripts/）

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-001](task-001-skill-models.md) Skill 数据模型 | 1 | 无 |
| [task-002](task-002-skill-runner.md) SkillRunner 状态机 | 1 | task-001 |
| [task-003](task-003-skill-registry.md) SkillRegistry + echo 测试 Skill | 1 | task-002 |
| [task-004](task-004-skill-api.md) Skill API 端点 | 1 | task-003 |
| [task-005](task-005-skill-sse.md) SSE Skill 事件推送 | 2 | task-004 |
| [task-006](task-006-skill-flow-panel.md) 前端 SkillFlowPanel | 3 | task-005 |

## 验收标准

1. 前端点击"启动测试 Skill" → 后端创建 echo Skill 实例 → 3 个 Step 自动执行 → SSE 实时推送每步状态 → 前端进度条从 Step 1 走到 Step 3 → 最终显示"完成"
2. 中途刷新页面 → OverviewPage 检测到未完成实例 → 点击恢复 → 从断点继续
3. `/api/tasks` 旧接口仍然正常工作（双轨并存）
