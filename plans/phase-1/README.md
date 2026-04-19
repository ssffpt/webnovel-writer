# Phase 1: Init 升级（6 步向导）

## 目标

将当前 3 步简化表单（CreateWizard）升级为 CLI 同等深度的 6 步初始化向导，确保后续 plan/write 有足够的上下文约束。

## 架构决策

- InitSkillHandler 实现 SkillHandler 接口，6 个 Step 中 4 个是 form，2 个是 confirm
- Step 5（创意约束包）需要后端调用 AI API 生成候选方案
- Step 6 确认后调用 `init_project.py`（通过 ScriptAdapter）+ 后处理 Patch
- 充分性闸门在 Step 6 前由后端校验，不通过则返回缺失项让用户补填

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-101](task-101-init-handler.md) InitSkillHandler 骨架 | 1 | Phase 0 |
| [task-102](task-102-init-steps-1-4.md) Step 1-4 表单采集 | 2 | task-101 |
| [task-103](task-103-init-step-5.md) Step 5 创意约束包生成 | 1 | task-102 |
| [task-104](task-104-init-step-6.md) Step 6 一致性复述 + 充分性闸门 + 执行 | 2 | task-103 |
| [task-105](task-105-init-wizard-ui.md) InitWizard 前端组件 | 3 | task-104 |
| [task-106](task-106-cleanup-create-wizard.md) 删除 CreateWizard + 迁移入口 | 2 | task-105 |

## 验收标准

1. 6 步向导完整走通 → state.json / 总纲 / 设定集 / idea_bank 全部生成
2. 充分性闸门拦截不完整提交（缺主角欲望 → 返回 Step 2 补填）
3. 创意约束包生成 2-3 套 → 用户选择 → 写入 idea_bank
4. 删除 CreateWizard 后，现有项目创建入口正常工作
