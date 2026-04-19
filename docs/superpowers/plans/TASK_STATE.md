# TASK_STATE.md — Web Workbench 修复任务执行状态

> 启动时间：2026-04-19
> 执行模式：subagent-driven-development
> 计划文件：`docs/superpowers/plans/2026-04-19-task-breakdown.md`

## 执行规则

- 每个 task 完成后必须通过验证命令才能标记完成
- 不得跳过已失败的 task
- Layer 0（文档）完成后合并一次 commit
- 后续每层完成后视情况合并 commit

---

## Layer 0：文档基线

| # | Task | 状态 | 验证命令 | 完成日期 |
|---|------|------|----------|----------|
| T01 | 更新 spec 桌面端布局规则 | ✅ done | `rg "桌面端（≥1200px）" docs/superpowers/specs/` | 2026-04-19 |
| T02 | 更新 spec 大纲页三级树定义 | ✅ done | `rg "章纲" docs/superpowers/specs/` | 2026-04-19 |
| T03 | 更新 spec 设定页双源模型定义 | ✅ done | `rg "setting_doc\|双源" docs/superpowers/specs/` | 2026-04-19 |
| T04 | 更新 spec 动作卡与任务系统合同 | ✅ done | `rg "confirm_label\|raw_logs\|honest" docs/superpowers/specs/` | 2026-04-19 |
| T05 | 更新 spec 总览页与活动流合同 | ✅ done | `rg "activityTimeline\|quickActions\|chapter_completion_ratio" docs/superpowers/specs/` | 2026-04-19 |
| T06 | 更新 spec 三条核心流程定义 | ✅ done | `rg "流程 1\|流程 2\|流程 3\|核心用户流程" docs/superpowers/specs/` | 2026-04-19 |

---

## Layer 1：后端合同

| # | Task | 状态 | 验证命令 | 完成日期 |
|---|------|------|----------|----------|
| T07 | outline/tree API 三级结构 | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k outline` | - |
| T08 | outline node 读写 API | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k outline_node` | - |
| T09 | settings nodes 列表 API | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k settings_nodes` | - |
| T10 | settings node 详情/保存/创建 API | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k settings_node_detail` | - |
| T11 | settings node insights API | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k insights` | - |
| T12 | activity_service + recent-activity API | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k activity` | - |
| T13 | workbench summary 增强字段 | pending | `python -m pytest dashboard/tests/test_phase1_contracts.py dashboard/tests/test_new_apis.py -v -k summary` | - |
| T14 | task_service 写入活动事件 | pending | `python -m pytest dashboard/tests/test_phase2_tasks.py -v` | - |
| T15 | watcher 扩展到正文/大纲/设定集 | pending | `python -m pytest dashboard/tests/test_new_apis.py -v -k watcher` | - |
| T16 | 聊天动作卡 rich 字段 | pending | `python -m pytest dashboard/tests/test_phase1_contracts.py dashboard/tests/test_phase3_chat.py -v` | - |
| T17 | models.py idle payload 扩展 | pending | `python -m pytest dashboard/tests/test_phase2_tasks.py -v` | - |
| T18 | 任务系统取消能力 + 双层日志 | pending | `python -m pytest dashboard/tests/test_phase2_tasks.py -v` | - |
| T19 | runner_bridge.py | pending | `python -c "from dashboard.runner_bridge import ExecutionHandle, run_command; print('OK')"` | - |
| T20 | claude_runner 真实桥接或诚实失败 | pending | `python -m pytest dashboard/tests/test_phase2_tasks.py -v` | - |
| T21 | inspect_setting 真实 insights 聚合 | pending | `python -m pytest dashboard/tests/test_phase2_tasks.py -v -k inspect` | - |

---

## Layer 2：前端数据层

| # | Task | 状态 | 验证命令 | 完成日期 |
|---|------|------|----------|----------|
| T22 | data.js normalizeSuggestedAction | pending | `node --test tests/workbench.chat.test.mjs tests/workbench.shell.test.mjs` | - |
| T23 | data.js normalizeTaskLogs | pending | `node --test tests/workbench.tasks.test.mjs` | - |
| T24 | data.js buildTopBarModel 收敛 | pending | `node --test tests/workbench.shell.test.mjs` | - |
| T25 | data.js buildOverviewModel 增强 | pending | `node --test tests/workbench.data.test.mjs` | - |
| T26 | api.js 新增 settings/outline API | pending | `node -e "import('./src/api.js').then(m => console.log(Object.keys(m).sort().join(',')))"` | - |

---

## Layer 3：前端壳层

| # | Task | 状态 | 验证命令 | 完成日期 |
|---|------|------|----------|----------|
| T27 | RightSidebarContent.jsx | pending | `npm run build` | - |
| T28 | RightSidebar.jsx 桌面端常驻 | pending | `npm run build` | - |
| T29 | AIAssistant.jsx 移动端浮层 | pending | `npm run build` | - |
| T30 | App.jsx 三栏布局 + 右栏接入 | pending | `npm run build` | - |
| T31 | TopBar.jsx 收敛纯导航 | pending | `npm run build` | - |
| T32 | index.css 桌面端右栏样式 | pending | `npm run build` | - |
| T33 | App.jsx dismiss/cancel/recent-activity | pending | `npm run build && node --test tests/workbench.shell.test.mjs tests/workbench.tasks.test.mjs tests/workbench.chat.test.mjs` | - |

---

## Layer 4：前端页面

| # | Task | 状态 | 验证命令 | 完成日期 |
|---|------|------|----------|----------|
| T34 | OutlinePage 三级树消费 | pending | `npm run build` | - |
| T35 | OutlinePage node 详情消费 | pending | `npm run build` | - |
| T36 | OutlinePage 辅助信息区 + 动作条 | pending | `npm run build` | - |
| T37 | ChapterPage 生成+审查按钮 | pending | `npm run build` | - |
| T38 | ChapterPage AI 结果摘要区 | pending | `npm run build` | - |
| T39 | SettingPage 迁移 settings API | pending | `npm run build` | - |
| T40 | SettingPage 新建条目 | pending | `npm run build` | - |
| T41 | SettingPage 关联提示区 + 检查冲突 | pending | `npm run build` | - |
| T42 | OverviewPage ready 态重做 | pending | `npm run build` | - |
| T43 | App.jsx 项目路径来源 + 动态跳转 | pending | `npm run build` | - |

---

## Layer 5：E2E 验收

| # | Task | 状态 | 验证命令 | 完成日期 |
|---|------|------|----------|----------|
| T44 | 桌面端右栏 E2E | pending | `npx playwright test e2e/workbench/right-sidebar.spec.ts` | - |
| T45 | 大纲三级树 E2E | pending | `npx playwright test e2e/workbench/outline-tree.spec.ts` | - |
| T46 | 三条核心流程 E2E | pending | `npx playwright test e2e/workbench/core-user-flows.spec.ts` | - |
| T47 | 总览页动态 E2E | pending | `npx playwright test e2e/workbench/overview-activity.spec.ts` | - |

---

## 里程碑

- [ ] Layer 0 完成（合并 commit）
- [ ] Layer 1 完成（settings 长链优先）
- [ ] Layer 2 完成
- [ ] Layer 3 完成
- [ ] Layer 4 完成
- [ ] Layer 5 完成（最终验收）

## 当前 next_action

**下一步**：T01 — 更新 spec 中桌面端布局规则
