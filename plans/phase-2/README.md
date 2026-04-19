# Phase 2: Plan 实现（卷级规划）

## 目标

实现 CLI `/webnovel-plan` 的完整 8 步流程，用户可在 OutlinePage 中启动卷级规划，生成节拍表、时间线、卷骨架、章节大纲。

## 架构决策

- PlanSkillHandler 实现 8 步状态机
- Step 4/4.5/5 是 auto→confirm 混合模式：后端生成后展示给用户确认
- Step 6 章节大纲分批生成（每批 4-5 章），通过 SSE 推送批次进度
- Step 7 回写设定集时，冲突标记 BLOCKER 需要用户决策（升级为 confirm）
- Step 8 的 7 项验证失败时，返回具体失败项 + 建议修复方案

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-201](task-201-plan-handler.md) PlanSkillHandler 骨架 + Step 1-3 | 1 | Phase 0 |
| [task-202](task-202-plan-beat-timeline.md) Step 4 节拍表 + Step 4.5 时间线 | 1 | task-201 |
| [task-203](task-203-plan-skeleton.md) Step 5 卷骨架 | 1 | task-202 |
| [task-204](task-204-plan-chapter-outlines.md) Step 6 章节大纲批量生成 | 1 | task-203 |
| [task-205](task-205-plan-writeback-validate.md) Step 7 回写设定集 + Step 8 验证 | 2 | task-204 |
| [task-206](task-206-plan-flow-ui.md) PlanFlow 前端组件 + OutlinePage 集成 | 3 | task-205 |

## 验收标准

1. 选择卷 → 节拍表/时间线/卷骨架生成并展示 → 用户确认
2. 章节大纲分批生成，前端显示"正在生成第 5/12 章"
3. 7 项验证全部通过 → 文件写入 → state.json 更新
4. 设定集回写冲突时弹出 BLOCKER 决策
