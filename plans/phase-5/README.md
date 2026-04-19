# Phase 5: Query 扩展

## 目标

将 SettingPage 从纯实体列表浏览升级为多维度查询工具，覆盖 CLI `/webnovel-query` 的 6 种查询类型。同时完善 OverviewPage 的创作仪表盘。

## 架构决策

- 不需要 SkillHandler（query 是即时查询，不是多步流程）
- 新增后端 API 端点直接查询 index.db + state.json
- 伏笔紧急度公式：`urgency = weight × (current_chapter - plant_chapter) / expected_payoff_window`
- 节奏分析基于 index.db 的 scenes 表 + strand 标记

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-501](task-501-foreshadow-api.md) 伏笔查询 API（紧急度计算） | 1 | Phase 0 |
| [task-502](task-502-rhythm-api.md) 节奏分析 API（Strand 连续/断档） | 1 | task-501 |
| [task-503](task-503-golden-finger-api.md) 金手指状态 + 债务查询 API | 1 | task-502 |
| [task-504](task-504-setting-page-tabs.md) SettingPage 标签页扩展 | 2 | task-503 |
| [task-505](task-505-overview-dashboard.md) OverviewPage 创作仪表盘 | 2 | task-504 |

## 验收标准

1. 伏笔标签页：三层分类 + 紧急度颜色标记（Critical 红 / Warning 黄 / Normal 绿）
2. 节奏标签页：Strand 连续/断档检测，断档超阈值显示警告
3. 金手指标签页：当前等级/技能/升级条件
4. 债务标签页：按紧急度排序
5. OverviewPage 仪表盘：总字数/章节进度/审查覆盖率/伏笔回收率
