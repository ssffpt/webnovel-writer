# Web Workbench 修复任务拆分

> **粒度规则**：每个 task 最多 3 个文件，必须有独立验证方式，完成标准明确。
>
> **执行原则**：按层顺序执行（后端→前端数据层→前端壳层→前端页面→E2E），层内可并行。每个 task 完成后必须通过验证命令才能进入下一个。

> **TASK_STATE.md**：执行状态跟踪文件，位于 `docs/superpowers/plans/TASK_STATE.md`。每次开始新 task 前必须先读取它，确认前置 task 已完成。

---

## Layer 0：文档基线

### T01. 更新 spec 中桌面端布局规则

- **文件**：`docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
- **内容**：把"AI 助手默认浮动，不再占据固定侧栏"改成桌面端常驻右栏、移动端退化浮层、专注模式隐藏右栏
- **验证**：`rg "桌面端（≥1200px）" docs/superpowers/specs/` 输出包含新规则
- **完成标准**：spec 中不再存在"不再占据固定侧栏"的旧口径

### T02. 更新 spec 中大纲页三级树定义

- **文件**：`docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
- **内容**：大纲页从"总纲+卷纲"改成"总纲→卷纲→章纲"三级结构，补辅助信息区和动作条规则
- **验证**：`rg "章纲" docs/superpowers/specs/` 输出包含新定义
- **完成标准**：spec 中明确三级树、辅助信息区字段、动作条启用条件

### T03. 更新 spec 中设定页双源模型定义

- **文件**：`docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
- **内容**：设定页增加 entity + setting_doc 双源模型、世界观分类、新建条目、关联提示区、检查冲突动作
- **验证**：`rg "setting_doc|双源" docs/superpowers/specs/` 有输出
- **完成标准**：spec 中明确节点分类、新建流程、insights 字段、检查冲突参数

### T04. 更新 spec 中动作卡与任务系统合同

- **文件**：`docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
- **内容**：冻结动作卡字段（label/description/scope/expected_result/confirm_label/cancel_label）、待确认=动作卡、任务取消接口、双层日志、真实执行或诚实失败
- **验证**：`rg "confirm_label|raw_logs|honest" docs/superpowers/specs/` 有输出
- **完成标准**：spec 中不再存在"preflight + extract-context = 已完成"的旧口径

### T05. 更新 spec 中总览页与活动流合同

- **文件**：`docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
- **内容**：总览页 ready 态结构、recent activity 合同、summary 增强字段、快捷入口、动态可点击跳转
- **验证**：`rg "activityTimeline|quickActions|chapter_completion_ratio" docs/superpowers/specs/` 有输出
- **完成标准**：spec 中明确活动事件类型、summary 增强字段列表

### T06. 更新 spec 中三条核心流程定义

- **文件**：`docs/superpowers/specs/2026-04-16-web-workbench-redesign.md`
- **内容**：补三条流程的目标交互、按钮入口、动作卡合同、完成判定标准
- **验证**：`rg "流程 1|流程 2|流程 3|核心用户流程" docs/superpowers/specs/` 有输出
- **完成标准**：spec 中明确页面按钮也走动作卡确认、没有真实执行器时必须 failed

---

## Layer 1：后端合同（按接口原子化）

### T07. 升级 outline/tree API 返回三级结构

- **文件**：`workbench_service.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：`GET /api/outline/tree` 返回 `{ summary, nodes, defaultNodeId }`，nodes 含 volume 和 chapter 子节点
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k outline`
- **完成标准**：tree 返回 nodes 含 chapter kind 子节点，每个 chapter 有 hasOutline/hasDraft/readyToWrite

### T08. 新增 outline node 读取/保存 API

- **文件**：`workbench_service.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：`GET /api/outline/nodes/{node_id}` 和 `POST /api/outline/nodes/{node_id}`，支持总纲/卷纲/章纲片段
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k outline_node`
- **完成标准**：可按 node_id 读取和保存，章纲片段保存不破坏相邻章节

### T09. 新增 settings nodes 列表 API

> **⚠️ Settings长链起点**：此Task是 T09→T10→T11→T21 串行链的第一步。链上任意Task出问题会影响整个依赖链，请优先处理并尽早验证通过。
>
- **文件**：新建 `settings_service.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：`GET /api/settings/nodes` 返回 categories + nodes，node 含 entity 和 setting_doc 两类
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k settings_nodes`
- **完成标准**：返回含世界观节点、实体节点和分类计数

### T10. 新增 settings node 详情/保存/创建 API

- **文件**：`settings_service.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：`GET/POST /api/settings/nodes/{id}`、`POST /api/settings/nodes`、详情含 title/content/meta/availableActions
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k settings_node_detail`
- **完成标准**：可创建人物实体节点和世界观文档节点，详情返回完整元数据

### T11. 新增 settings node insights API

- **文件**：`settings_service.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：`GET /api/settings/nodes/{id}/insights` 返回 linkedChapterCount/recentChapters/conflicts
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k insights`
- **完成标准**：insights 含关联章节数、最近出现章节、冲突列表（可为空但结构存在）

### T12. 新建 activity_service 并修复 recent-activity API

- **文件**：新建 `activity_service.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：活动落盘到 `.webnovel/dashboard_activity.jsonl`，`GET /api/recent-activity` 读取真实数据
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k activity`
- **完成标准**：保存文件后 recent-activity 返回对应 file_modified 事件

### T13. 增强 workbench summary 返回字段

> **⚠️ T25依赖此Task**：buildOverviewModel 需要从本Task获取 recent_tasks/recent_changes 字段
>
- **文件**：`workbench_service.py`、`tests/test_new_apis.py`、`tests/test_phase1_contracts.py`
- **内容**：summary 补齐 project.path/created_at、progress.target_words/target_chapters/chapter_completion_ratio/word_completion_ratio/outline_files/setting_files、recent_tasks/recent_changes 从 activity_service 读取
- **验证**：`python -m pytest dashboard/tests/test_phase1_contracts.py dashboard/tests/test_new_apis.py -v -k summary`
- **完成标准**：summary 包含所有增强字段，recent_tasks/recent_changes 不再永远为空

### T14. 让 task_service 在任务完成/失败时写入活动

- **文件**：`task_service.py`、`activity_service.py`、`tests/test_phase2_tasks.py`
- **内容**：TaskService 注入 activity callback，mark_completed/mark_failed 后写入 task_completed/task_failed 事件
- **验证**：`python -m pytest dashboard/tests/test_phase2_tasks.py -v`
- **完成标准**：任务完成后 recent-activity 出现 task_completed 事件

### T15. 扩展 watcher 监听范围到正文/大纲/设定集

- **文件**：`watcher.py`、`app.py`、`tests/test_new_apis.py`
- **内容**：从只监听 `.webnovel/` 扩展到监听 `正文/大纲/设定集`，SSE 事件补齐 path/page 字段，文件修改写入 activity
- **验证**：`python -m pytest dashboard/tests/test_new_apis.py -v -k watcher`
- **完成标准**：保存正文文件后 SSE 推送含 path 和 page 的 file.changed 事件

### T16. 聊天动作卡补齐 rich 字段

- **文件**：`workbench_service.py`、`tests/test_phase1_contracts.py`、`tests/test_phase3_chat.py`
- **内容**：suggested_actions 每个 action 补齐 description/scope/expected_result/confirm_label/cancel_label
- **验证**：`python -m pytest dashboard/tests/test_phase1_contracts.py dashboard/tests/test_phase3_chat.py -v`
- **完成标准**：每个 suggested_action 含完整 6 字段，scope 含 page 和 path

### T17. 扩展 models.py idle payload 与任务字段

> **前置条件**：无。本Task可最先执行，为T18提供字段命名依据。
>
- **文件**：`models.py`、`task_service.py`、`tests/test_phase2_tasks.py`
- **内容**：TASK_IDLE_PAYLOAD 补齐 raw_logs/can_cancel/execution_mode 字段
- **验证**：`python -m pytest dashboard/tests/test_phase2_tasks.py -v`
- **完成标准**：idle payload 与前端 IDLE_TASK 字段对齐

### T18. 任务系统增加取消能力和双层日志

> **前置条件**：T17（models.py idle payload）必须先完成，以定义字段名称。
>
- **文件**：`task_service.py`、`app.py`、`tests/test_phase2_tasks.py`
- **内容**：新增 `cancel_task()`、`append_raw_log()`、`POST /api/tasks/{id}/cancel`、任务对象增加 raw_logs/can_cancel/execution_mode 字段
- **验证**：`python -m pytest dashboard/tests/test_phase2_tasks.py -v`
- **完成标准**：取消接口返回 cancelled 状态，已完成任务同时含 logs 和 raw_logs

### T19. 新建 runner_bridge.py 可取消执行句柄

- **文件**：新建 `runner_bridge.py`
- **内容**：ExecutionHandle 类（cancel_event + process 引用 + cancel 方法）、run_command 统一 subprocess 入口、friendly/raw 双回调
- **验证**：`python -c "from dashboard.runner_bridge import ExecutionHandle, run_command; print('OK')"`
- **完成标准**：模块可导入，ExecutionHandle 可实例化

### T20. claude_runner 改为真实桥接或诚实失败

> **前置条件**：T19（runner_bridge.py）必须已完成并可导入
>
- **文件**：`claude_runner.py`、`runner_bridge.py`、`tests/test_phase2_tasks.py`
- **内容**：删除所有"preflight + extract-context = completed"路径，无真实执行器时返回 failed + 明确错误，有执行器时走 runner_bridge
- **验证**：`python -m pytest dashboard/tests/test_phase2_tasks.py -v`
- **完成标准**：无真实执行器时 write_chapter/review_chapter/plan_outline 返回 failed，inspect_setting 返回 query_adapter 结果

### T21. inspect_setting 改为真实 insights 聚合

> **⚠️ Settings长链终点**：依赖 T11（settings_service.insights API）已完成。本Task是settings链路的最后一步。
>
- **文件**：`claude_runner.py`、`settings_service.py`、`tests/test_phase2_tasks.py`
- **内容**：inspect_setting 不再只做文件存在校验，改为调用 settings_service 聚合 linkedChapterCount/recentChapters/conflicts，返回结构化 summary
- **验证**：`python -m pytest dashboard/tests/test_phase2_tasks.py -v -k inspect`
- **完成标准**：inspect_setting 完成后 result 含 summary + insights，不再只有路径存在校验

---

## Layer 2：前端数据层

### T22. data.js 补齐动作卡 normalize 函数

- **文件**：`data.js`、`tests/workbench.chat.test.mjs`、`tests/workbench.shell.test.mjs`
- **内容**：新增 `normalizeSuggestedAction()`，buildChatReplyModel 和 buildRightSidebarModel 统一使用它处理 suggested_actions
- **验证**：`node --test tests/workbench.chat.test.mjs tests/workbench.shell.test.mjs`
- **完成标准**：动作卡对象保证含 description/scope/expectedResult/confirmLabel/cancelLabel

### T23. data.js 补齐任务日志 normalize 函数

- **文件**：`data.js`、`tests/workbench.tasks.test.mjs`
- **内容**：新增 `normalizeTaskLogs()`，buildRightSidebarModel 的 currentTask 增加 rawLogs/canCancel 字段
- **验证**：`node --test tests/workbench.tasks.test.mjs`
- **完成标准**：currentTask 含 rawLogs（数组）和 canCancel（布尔）

### T24. data.js 收敛 buildTopBarModel 移除 taskBadge

- **文件**：`data.js`、`tests/workbench.shell.test.mjs`
- **内容**：buildTopBarModel 只返回 `{ pages, activePage }`，不再返回 title 和 taskBadge
- **验证**：`node --test tests/workbench.shell.test.mjs`
- **完成标准**：buildTopBarModel 输出不含 taskBadge 和 title

### T25. data.js 增强 buildOverviewModel

> **前置条件**：T13（summary增强）必须先完成，因为依赖 recent_tasks/recent_changes 字段
>
- **文件**：`data.js`、`tests/workbench.data.test.mjs`
- **内容**：buildOverviewModel 输出增加 activityTimeline/quickActions/progressHighlights，新增 buildOverviewQuickActions/normalizeActivityTimeline/resolveOverviewActivityTarget 三个纯函数
- **验证**：`node --test tests/workbench.data.test.mjs`
- **完成标准**：buildOverviewModel(summary, activities, currentTask) 返回含 quickActions 和 activityTimeline

### T26. api.js 新增 settings 和 outline API 封装

- **文件**：`api.js`
- **内容**：新增 fetchSettingsNodes/fetchSettingsNode/saveSettingsNode/createSettingsNode/fetchSettingsInsights、fetchOutlineNodes/fetchOutlineNode/saveOutlineNode、cancelTask
- **验证**：`node -e "import('./src/api.js').then(m => console.log(Object.keys(m).sort().join(',')))"` 输出含新函数名
- **完成标准**：所有新 API 函数可导入

---

## Layer 3：前端壳层

> **并行说明**：T27 和 T29 可并行执行（互相不依赖）。T28 依赖 T27 确认 RightSidebarContent 的导出名。T30 依赖 T28+T29。
>
### T27. 新建 RightSidebarContent.jsx 抽取共享内容

> **可与 T29 并行执行**
>
- **文件**：新建 `RightSidebarContent.jsx`
- **内容**：从 AIAssistant.jsx 抽取消息列表、动作卡（含 rich 字段渲染）、任务状态（含取消按钮和日志切换）、输入表单
- **验证**：`npm run build`
- **行为验证**：启动 dev server，桌面端右栏区域渲染出消息列表、动作卡、任务状态、输入表单四块内容；无 JS 报错
- **完成标准**：构建成功，RightSidebarContent 可被导入

### T28. 新建 RightSidebar.jsx 桌面端常驻右栏

> **依赖**：T27（需确认 RightSidebarContent 的导出路径）
>
- **文件**：新建 `RightSidebar.jsx`
- **内容**：桌面端常驻侧栏容器，引用 RightSidebarContent
- **验证**：`npm run build`
- **行为验证**：桌面端页面右侧出现常驻侧栏，显示"AI 助手"标题和 RightSidebarContent 内容；移动端不显示此侧栏
- **完成标准**：构建成功

### T29. 改造 AIAssistant.jsx 为移动端浮层

> **可与 T27 并行执行**
>
- **文件**：`AIAssistant.jsx`
- **内容**：改为引用 RightSidebarContent，自身只负责 FAB 按钮和弹层外壳，接收 model prop 而非分散 props
- **验证**：`npm run build`
- **行为验证**：移动端视口下右下角 FAB 按钮可见，点击后弹出对话框；桌面端 FAB 不显示
- **完成标准**：构建成功，AIAssistant 内部使用 RightSidebarContent

### T30. App.jsx 恢复三栏布局并接入右栏

- **文件**：`App.jsx`
- **内容**：workbench-body 改为 grid 双列，引入 RightSidebar，构建 rightSidebarModel，TopBar 传入新 model（无 taskBadge）
- **验证**：`npm run build`
- **行为验证**：桌面端页面分为左右两栏，左栏是页面工作区，右栏是 AI 助手常驻栏；TopBar 只显示导航按钮和项目切换器，无任务状态
- **完成标准**：构建成功，桌面端存在 .workbench-right 节点

### T31. TopBar.jsx 收敛为纯导航

- **文件**：`TopBar.jsx`
- **内容**：移除连接状态 dot 和任务 badge，只保留页面导航按钮和项目切换器，model 只读 pages 和 activePage
- **验证**：`npm run build`
- **行为验证**：TopBar 只渲染页面导航按钮和项目切换器，不再显示连接状态圆点和任务标签
- **完成标准**：TopBar 不再渲染 taskBadge 和 connected

### T32. index.css 恢复桌面端右栏样式

- **文件**：`index.css`
- **内容**：workbench-body 桌面端 grid-template-columns: minmax(0,1fr) 320px；.workbench-right 固定右栏；ai-fab/ai-dialog 桌面端隐藏；<1200px 回退单列+浮层
- **验证**：`npm run build`
- **行为验证**：桌面端右栏固定 320px 宽度，不随页面滚动；FAB 按钮桌面端不可见；缩小窗口至 <1200px 时右栏消失、FAB 出现
- **完成标准**：构建成功，桌面端右栏可见、FAB 隐藏

### T33. App.jsx 接入 dismiss/cancel/recent-activity 刷新

- **文件**：`App.jsx`
- **内容**：新增 handleDismissAction/handleCancelTask，SSE 更新时带 raw_logs/can_cancel，recent-activity 在 file.changed/task.updated 后刷新
- **验证**：`npm run build && node --test tests/workbench.shell.test.mjs tests/workbench.tasks.test.mjs tests/workbench.chat.test.mjs`
- **行为验证**：在右栏点击动作卡"先不执行"按钮，动作卡消失；聊天发送消息后动作卡出现；任务执行中点"取消任务"按钮可取消
- **完成标准**：构建和纯函数测试通过

---

## Layer 4：前端页面

### T34. OutlinePage 消费三级 outline tree API

- **文件**：`OutlinePage.jsx`
- **内容**：左栏从"固定节点+卷列表"改为消费 /api/outline/tree 的 nodes 渲染三级树，章节点显示 hasOutline/hasDraft/readyToWrite 状态
- **验证**：`npm run build`
- **行为验证**：打开大纲页，左栏可见总纲→卷纲→章纲三级树；卷节点可展开显示章子节点；章节点旁有状态标记（✓有章纲/✓有正文/●建议写作）
- **完成标准**：左栏可见总纲→卷纲→章纲三级，章节点有状态标记

### T35. OutlinePage 消费 outline node 详情 API

- **文件**：`OutlinePage.jsx`
- **内容**：选中节点时通过 /api/outline/nodes/{id} 加载内容，章纲节点编辑自己的片段而非整卷文件，保存也走 node API
- **验证**：`npm run build`
- **行为验证**：选中总纲节点，编辑区显示总纲内容；选中卷纲节点，显示卷纲内容；选中章纲节点，只显示本章内容而非整卷文件；保存后切换回来内容不丢失
- **完成标准**：选中章纲节点时编辑区只显示本章内容

### T36. OutlinePage 加入辅助信息区和动态动作条

- **文件**：`OutlinePage.jsx`
- **内容**：编辑器上方展示已拆章数/已有正文数/建议下一步；底部动作条根据节点状态动态启用：保存/生成卷纲/生成章纲/开始写本章
- **验证**：`npm run build`
- **行为验证**：选中卷纲节点时，编辑区上方显示"已拆章 N 章/已有正文 N 章"；底部动作条"生成章纲"按钮可点击（非🔒）；选中章纲且 readyToWrite 时底部显示"开始写本章"按钮
- **完成标准**：选中卷纲时显示"生成章纲"按钮（非永久🔒），选中章纲且 readyToWrite 时显示"开始写本章"

### T37. ChapterPage 增加"按大纲生成"和"审查本章"按钮

- **文件**：`ChapterPage.jsx`
- **内容**：编辑器操作区新增两个按钮，点击后构造 suggested_action 展示在右栏动作卡区（不直接创建任务）
- **验证**：`npm run build`
- **行为验证**：打开章节页，编辑器操作区可见"按大纲生成"和"审查本章"两个按钮；点击任一按钮后右栏出现对应动作卡（含标题、说明、作用对象、预计结果、执行/取消按钮）
- **完成标准**：按钮可见，点击后右栏出现对应动作卡

### T38. ChapterPage 增加 AI 结果摘要区

- **文件**：`ChapterPage.jsx`
- **内容**：编辑区下方展示最近一次 write_chapter/review_chapter 任务结果摘要
- **验证**：`npm run build`
- **行为验证**：在右栏触发一个 write_chapter 或 review_chapter 任务，任务完成后章节页编辑区下方出现结果摘要文字
- **完成标准**：任务完成后摘要区可见

### T39. SettingPage 迁移到 settings nodes API

- **文件**：`SettingPage.jsx`
- **内容**：从 /api/entities 切换到 /api/settings/nodes，左栏支持 entity + setting_doc 双类节点，分类含世界观
- **验证**：`npm run build`
- **行为验证**：打开设定页，左栏分类标签显示"全部/人物/势力/地点/世界观/物品/招式"；点击"世界观"分类后出现世界观文档节点卡片；切换回"人物"出现实体节点
- **完成标准**：左栏显示人物/势力/地点/世界观/物品/招式分类，世界观节点可见

### T40. SettingPage 增加名称输入和新建条目

- **文件**：`SettingPage.jsx`
- **内容**：编辑区顶部加名称输入框，左栏加"＋新建条目"按钮，创建后自动选中和刷新
- **验证**：`npm run build`
- **行为验证**：点击左栏"＋新建条目"，弹出小表单填分类和名称，确认后左栏刷新、新条目自动选中、编辑区顶部名称输入框显示新名称
- **完成标准**：可新建人物和世界观条目，自动选中进入编辑

### T41. SettingPage 增加关联提示区和启用检查冲突

- **文件**：`SettingPage.jsx`
- **内容**：编辑区下方展示 insights（关联章节数/最近出现章节/潜在冲突），"检查冲突"按钮不再🔒，点击后构造 suggested_action
- **验证**：`npm run build`
- **行为验证**：选中任一设定节点，编辑区下方显示关联提示区（关联章节数、最近出现章节、潜在冲突列表）；"检查冲突"按钮不再是🔒，可点击，点击后右栏出现 inspect_setting 动作卡
- **完成标准**：insights 区可见，检查冲突按钮可点击

### T42. OverviewPage 重做 ready 态布局

- **文件**：`OverviewPage.jsx`
- **内容**：ready 态增加快捷入口卡组（继续写作/去大纲/去设定/查看当前任务）、创作进度（章节/字数比例）、最近动态时间线（可点击跳转）
- **验证**：`npm run build`
- **行为验证**：打开总览页，ready 态可见4个快捷入口卡片（继续写作/去大纲/去设定/查看当前任务）；项目概况区显示章节进度和字数进度比例；最近动态时间线有内容且每项可点击跳转
- **完成标准**：ready 态展示 4 个快捷入口、进度比例、可点击动态列表

### T43. App.jsx 修项目路径来源和动态跳转

- **文件**：`App.jsx`
- **内容**：新增 currentProjectPath 独立状态（不依赖 summary.project.path），总览页动态点击跳转到对应页面并选中文件
- **验证**：`npm run build`
- **行为验证**：ProjectSwitcher 下拉中当前项目高亮；总览页点击动态中文件项，页面跳转到对应页面并选中该文件
- **完成标准**：ProjectSwitcher 正确高亮当前项目，动态点击可跳转

---

## Layer 5：E2E 验收

### T44. 桌面端右栏 E2E

- **文件**：新建 `e2e/workbench/right-sidebar.spec.ts`
- **内容**：桌面端右栏常驻、专注模式隐藏、移动端退化浮层
- **验证**：`npx playwright test e2e/workbench/right-sidebar.spec.ts`
- **完成标准**：3 个场景通过

### T45. 大纲三级树 E2E

- **文件**：新建 `e2e/workbench/outline-tree.spec.ts`
- **内容**：选中总纲/卷纲/章纲加载正确内容，动作条状态切换
- **验证**：`npx playwright test e2e/workbench/outline-tree.spec.ts`
- **完成标准**：三级树可导航，章纲节点可编辑

### T46. 三条核心流程 E2E

- **文件**：新建 `e2e/workbench/core-user-flows.spec.ts`
- **内容**：流程1（选章纲→生成章节）、流程2（编辑正文→审查本章）、流程3（修改设定→检查冲突）
- **验证**：`npx playwright test e2e/workbench/core-user-flows.spec.ts`
- **完成标准**：3 条流程端到端可走通（执行器不可用时诚实失败也算通过）

### T47. 总览页动态 E2E

- **文件**：新建 `e2e/workbench/overview-activity.spec.ts`
- **内容**：保存文件后最近动态可见、任务完成后动态可见、动态点击跳转
- **验证**：`npx playwright test e2e/workbench/overview-activity.spec.ts`
- **完成标准**：动态列表有内容，点击可跳转

---

## 执行顺序总览

```
Layer 0: T01→T02→T03→T04→T05→T06（文档，可合并一次 commit）
    ↓
Layer 1: T07→T08（outline）
       | T09→T10→T11→T21（settings长链 ⚠️ 不可并行）
       | T12→T13→T14→T15（activity/summary）
       | T16（rich action）
       | T17（idle payload）→ T18（task cancel）  ⚠️ T17先于T18
       | T19 → T20（runner）  ⚠️ T20依赖T19
    ↓  （并行建议：T07/T12/T16/T17/T19 可并行；settings长链单独串行）
Layer 2: T22 ∥ T23 ∥ T24 可并行 | T25（依赖T13） | T26（独立）
    ↓
Layer 3: T27 ∥ T29（可并行）→ T28（依赖T27）→ T30→T31→T32→T33
    ↓
Layer 4: T34→T35→T36（outline）| T37→T38（chapter）| T39→T40→T41（setting）| T42→T43（overview）
    ↓  （4 个页面可并行）
Layer 5: T44→T45→T46→T47
```

### 关键路径说明

| 链路 | Task序列 | 风险 |
|------|----------|------|
| **Settings长链** | T09→T10→T11→T21 | 串行不可拆，任意一个出问题会delay整个依赖 |
| **Task字段定义** | T17→T18 | T17先定义idle payload，T18才能用字段名 |
| **Runner执行** | T19→T20 | T20强依赖T19的runner_bridge模块 |
| **壳层组装** | (T27∥T29)→T28→T30 | T27+T29并行节省时间，T28等T27 |

**全程回归命令**（每个 task 完成后必须通过）：

```bash
# 后端
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer && python -m pytest dashboard/tests/ -v

# 前端
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard/frontend && node --test tests/workbench.*.mjs && npm run build
```
