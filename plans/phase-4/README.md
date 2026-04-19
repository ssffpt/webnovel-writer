# Phase 4: Review 实现

## 目标

实现 CLI `/webnovel-review` 的完整 8 步流程，支持单章和范围审查，六维并行检查，critical 问题用户决策。

## 架构决策

- ReviewSkillHandler 实现 8 步状态机
- Step 3 六维审查复用 Phase 3 的检查器基础设施（同一套 Checker，不同调用入口）
- Step 7 critical 问题是 confirm 模式：展示问题 + 修复方案选项 → 用户选择
- 审查报告写入 `.webnovel/审查报告/` 目录
- review_metrics 写入 index.db

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-401](task-401-review-handler.md) ReviewSkillHandler 骨架 + Step 1-2 | 1 | Phase 0 |
| [task-402](task-402-review-checkers.md) Step 3 并行审查（复用 Phase 3 检查器） | 1 | task-401 |
| [task-403](task-403-review-report.md) Step 4 审查报告生成 + Step 5-6 落库 | 2 | task-402 |
| [task-404](task-404-review-critical.md) Step 7 critical 问题决策 + Step 8 收尾 | 1 | task-403 |
| [task-405](task-405-review-flow-ui.md) ReviewFlow 前端组件 + 六维雷达图 | 3 | task-404 |

## 验收标准

1. 选择章节范围 → 6 维并行审查 → 各维度进度实时推送
2. 审查报告生成 → 6 维评分 + 问题列表
3. review_metrics 写入 index.db → state.json 更新
4. critical 问题弹出决策对话框 → 用户选择修复方案
5. 六维雷达图正确渲染
