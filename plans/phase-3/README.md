# Phase 3: Write 实现（章节创作）

## 目标

实现 CLI `/webnovel-write` 的完整 6 步流程（含 RAG 降级模式），这是整个系统最核心的能力。

## 架构决策

- WriteSkillHandler 实现 6 步状态机，支持 standard/fast/minimal 三种模式
- Context Agent（Step 1）在无 RAG 时降级为文件系统加载（总纲 + 设定集 + 前 N 章摘要）
- Step 3 六维审查必须由独立检查器执行（不可内联伪造），通过 asyncio.gather 并行
- Data Agent（Step 5）调用 scripts/data_modules/ 完成实体提取、摘要、状态更新
- Git 备份（Step 6）默认关闭，通过 config.json 开启
- ScriptAdapter 在此 Phase 首次真正调用 scripts/（extract-context、data_modules 等）

## Task 列表

| Task | 文件数 | 依赖 |
|------|--------|------|
| [task-301](task-301-script-adapter.md) ScriptAdapter 实现（extract-context + data_modules 封装） | 1 | Phase 0 |
| [task-302](task-302-write-handler.md) WriteSkillHandler 骨架 + 模式选择 | 1 | task-301 |
| [task-303](task-303-context-agent.md) Step 1 Context Agent（含 RAG 降级） | 2 | task-302 |
| [task-304](task-304-drafting.md) Step 2A 正文起草 + Step 2B 风格适配 | 1 | task-303 |
| [task-305](task-305-review-checkers.md) Step 3 六维审查（并行检查器） | 2 | task-304 |
| [task-306](task-306-polish.md) Step 4 润色 + Anti-AI 终检 | 1 | task-305 |
| [task-307](task-307-data-agent.md) Step 5 Data Agent + Step 6 Git 备份 | 2 | task-306 |
| [task-308](task-308-write-flow-ui.md) WriteFlow 前端组件 + ChapterPage 集成 | 3 | task-307 |

## 验收标准

1. 选择章节 → AI 创作模式 → 6 步流程走完
2. 正文文件 + review_metrics + 摘要 + state 更新全部落盘
3. 三种模式（standard/fast/minimal）行为正确（fast 跳过 2B，minimal 仅核心 3 项审查）
4. 失败可从断点恢复
5. 无 RAG 时 Step 1 日志标注降级模式，功能正常
