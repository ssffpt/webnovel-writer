# Web Workbench 用户流程重设计

> 日期：2026-04-16
> 状态：待审阅
> 设计稿：`docs/design-mockups/v4-all-pages.html`（主页面设计）、`docs/design-mockups/v4.1-supplements.html`（补充：创建向导、未完成设置状态、章节页空状态）

## 背景

当前 Web Workbench 存在三个核心问题：

1. **无入口**：用户打开网页后，没有"创建新小说"的入口，不知道从哪开始
2. **流程不清**：页面信息混乱，用户不知道先做什么后做什么
3. **编辑区太小**：AI 助手面板固定占右侧 1/4，挤压写作空间；三个内容页套用同一模板，缺乏针对性

目标：面向不会编码的用户，让纯网页端就能完成"开始写小说"的全流程。前端 UI 和后端 API 同步设计，前后端同步开发。

## 用户流程模型

采用两阶段模型，非严格线性：

**阶段 1：起步（一次性）** — 创建项目 → 完成设定 → 规划大纲

**阶段 2：写作循环（日常）** — 逐章写作，随时可查设定/改大纲/加人物，可选 AI 审查

审查不是必经步骤，而是可选的辅助工具（AI 6轴审稿：爽点密度、一致性、节奏、OOC、连贯性、吸引力）。

## 项目状态

| 状态 | 判断条件 | 总览页行为 |
|------|---------|-----------|
| 无项目 | `.webnovel/state.json` 不存在 | 显示空状态 + "创建新小说"按钮 |
| 未完成设置 | state.json 存在但 `project_info.title` 或 `project_info.genre` 为空 | 显示步骤引导条（起步阶段未完成）+ 项目概况（已有字段）+ "继续设置"按钮（点击打开创建向导，预填已有信息） |
| 项目就绪 | state.json 存在且 `project_info.title` 和 `project_info.genre` 均非空 | 显示步骤引导条 + 下一步建议 |

## 全局组件

### 顶栏
- **左侧**：页面导航标签，带序号暗示流程 — ①总览 / ②大纲 / ③设定 / ④章节
- **右侧**：项目切换器（醒目样式）；无项目时显示"选择项目 ▾"

### AI 助手
- 右下角浮动 💬 按钮，全局可用
- 默认收起，点击展开对话框
- 对话框包含：消息区 + 动作卡 + 输入框
- 不再占据固定侧栏面板

### 禁用按钮策略
- 不可用操作：虚线边框 + 🔒 图标 + tooltip 说明条件（如"先完成大纲才能生成章纲"）
- 不使用灰色禁用（opacity:0.5），避免用户困惑

## 页面设计

### 总览页（默认页面）

**空状态（无项目）**：
- 居中大号欢迎文案："欢迎来到网文创作台"
- 简短说明
- "＋ 创建新小说"大按钮（发光效果）

**未完成设置**（state.json 存在但 title 或 genre 为空）：
- 步骤引导条显示起步阶段未完成
- 项目概况区显示已有信息（可能只有部分字段）
- 醒目提示条："项目设置尚未完成" + "继续设置"按钮（点击打开创建向导，预填已有信息）

**项目就绪时**，从上到下：

1. **步骤引导条**（视觉核心）
   - 起步 ✓ → ✏️ 写作中 → 🔍 审查
   - 当前阶段高亮发光，已完成显示 ✓
   - 底部显示当前状态文本（如"当前：第3章已完成"）

2. **"下一步"行动卡**（最醒目的行动入口）
   - 一句话说明下一步
   - 大号操作按钮（发光效果）
   - 辅助操作按钮（审查等）

3. **项目概况 + 最近动态**（并排）
   - 项目概况：书名、题材、当前章节、总字数、创建日期
   - 最近动态：合并任务+修改为单条时间线（时间 + 事件描述）

### 大纲页

- **左侧**（220px）：树形缩进列表
  - 总纲 → 第N卷 → 卷纲/节拍表/时间线
  - 已有卷标注 ✓
  - 待生成项改为可点击操作："＋ 生成第N卷大纲"
- **右侧**：大编辑区
- **按钮**：保存、生成卷纲🔒、生成章纲🔒（带 tooltip）

### 设定页

- **左侧**（220px）：卡片式实体列表
  - 分类筛选标签（含数量）：全部(N) / 人物(N) / 势力(N) / 地点(N) / 世界观(N)
  - 每张卡片：实体名（含图标）+ 一行摘要（单行省略）
  - 选中卡片高亮
- **右侧**：大编辑区
- **按钮**：保存、检查冲突🔒（带 tooltip）

### 章节页

**空状态（无章节）**：
- 左侧列表区显示"还没有章节"
- 右侧编辑区显示引导："开始写第1章吧！" + "写第1章"按钮

**有章节时**：
- **左侧**（140px，可折叠）：章节列表
  - **倒序排列**（最新章节置顶）
  - 当前章节高亮 ✓
  - 底部有"＋ 写第N章"操作入口
- **右侧**：大编辑区
  - 顶部：文件路径 + **专注模式按钮**（绿色醒目样式）
  - 底部状态栏：操作按钮 + **字数统计**（"本章：X 字"）
- **专注模式**：隐藏左侧列表和 AI 助手，全屏写作。按 ESC 或点击右上角退出按钮退出。

## 创建向导（3步）

点击"创建新小说"后进入分步弹窗：

**第1步：基本信息**
- 书名（必填）
- 题材类型（标签多选：修仙/都市/系统流/古言/规则怪谈...，可组合。选项来自 `webnovel-writer/genres/` 子目录名，如 `xuanhuan`→"修仙"、`dog-blood-romance`→"狗血言情"，通过 `genre-profiles.md` 的映射表转为中文显示名）
- 目标字数（默认 200 万，可改）
- 目标章节数（默认 600，可改）
- 核心卖点（可选）

**第2步：主角设定**（可选，底部有"跳过此步 →"链接）
- 主角名字
- 金手指名称
- 金手指类型（系统流/鉴定流/签到流/空间流/无金手指...，选项来自 `templates/golden-finger-templates.md` 中定义的类型列表；"无金手指"选项突出显示）

**第3步：确认创建**
- 展示填写信息摘要
- 点击"创建项目"
- 后端调用 `init_project.py` 生成项目结构和模板文件

## 页面跳转规则

| 触发位置 | 操作 | 跳转行为 |
|---------|------|----------|
| 总览页 | 点击"写第N章" | 跳转到章节页，自动选中第N章（如不存在则创建空文件并打开） |
| 总览页 | 点击"审查" | 跳转到章节页，打开 AI 助手并发送审查指令 |
| 总览页 | 点击"继续设置" | 打开创建向导（预填已有信息） |
| 总览页 | 最近动态中点击文件 | 跳转到对应页面（章节/大纲/设定）并选中该文件 |
| 大纲页 | 点击"＋ 生成第N卷大纲" | 打开 AI 助手并发送规划指令（后端对接后实际执行） |
| 章节页 | 点击"＋ 写第N章" | 创建空文件并打开编辑器 |
| 章节页 | 点击"按大纲生成" | 打开 AI 助手并发送写作指令 |
| 章节页 | 点击"审查本章" | 打开 AI 助手并发送审查指令 |
| 章节页 | 点击"专注模式" | 隐藏侧栏和 AI 助手，编辑区全屏 |
| 专注模式 | 按 ESC / 点击退出按钮 | 恢复正常布局 |
| 创建向导 | 点击"创建项目" | 关闭弹窗，跳转到总览页（项目就绪状态） |

## 前后端交互设计

### 现有 API 复用

后端已有一组可用的 API（`app.py`），直接复用：

| 功能 | API | 用途 |
|------|-----|------|
| 项目信息 | `GET /api/project/info` | 总览页项目概况、项目状态判断 |
| Workbench 摘要 | `GET /api/workbench/summary` | 总览页项目概况 + 进度 |
| 文件树 | `GET /api/files/tree` | 大纲页树结构、章节页列表 |
| 读取文件 | `GET /api/files/read` | 编辑区加载文件内容 |
| 保存文件 | `POST /api/files/save` | 编辑区保存修改 |
| 实体列表 | `GET /api/entities?type=` | 设定页左侧卡片列表（支持 type 过滤） |
| 实体详情 | `GET /api/entities/{id}` | 设定页右侧编辑区 |
| 章节列表 | `GET /api/chapters` | 章节页左侧列表、总览页当前章节 |
| 关系列表 | `GET /api/relationships` | 设定页关联信息 |
| 状态变化 | `GET /api/state-changes` | 最近动态数据源 |
| 聊天 | `POST /api/chat` | AI 助手对话 |
| 创建任务 | `POST /api/tasks` | 执行动作（写作/审查/规划/检查设定） |
| 任务状态 | `GET /api/tasks/{id}` | 轮询任务执行状态 |
| 当前任务 | `GET /api/tasks/current` | 总览页任务状态 |
| SSE 推送 | `GET /api/events` | 实时更新（文件变更 + 任务状态） |

### 新增 API

#### 1. 创建项目 `POST /api/project/create`

创建向导第3步"确认创建"调用。后端内部调用 `init_project.py`，创建目录结构、生成 state.json 和模板文件。

**请求体**：
```json
{
  "title": "我的修仙小说",
  "genre": "修仙+系统流",
  "target_words": 2000000,
  "target_chapters": 600,
  "core_selling_points": "无敌系统，一路碾压",
  "protagonist_name": "林凡",
  "golden_finger_name": "诸天万界系统",
  "golden_finger_type": "系统流"
}
```

**响应**：
```json
{
  "success": true,
  "project_root": "/path/to/project",
  "state": { ... }
}
```

**project_dir 生成策略**：请求体不含 `project_dir`，由后端自动生成。规则：
1. 读取服务端配置的项目根目录（默认 `~/webnovel-projects/`，可通过环境变量 `WEBNOVEL_PROJECTS_ROOT` 覆盖）
2. 在该目录下创建以书名命名的子目录：`{root}/{title}/`
3. 若子目录已存在，追加数字后缀：`{root}/{title}-2/`
4. 创建成功后将项目注册到 `~/.claude/webnovel-writer/workspaces.json`（复用 `project_locator.py` 的注册机制）

**后端实现**：在 `app.py` 中新增路由，内部调用 `init_project.init_project()` 函数（直接 Python 调用，非 subprocess）。`init_project()` 已是可 import 的函数，请求体字段与函数参数一一对应。

#### 2. 项目列表 `GET /api/projects`

项目切换器数据源。

**响应**：
```json
{
  "projects": [
    {
      "name": "我的修仙小说",
      "path": "/path/to/project",
      "genre": "修仙",
      "current_chapter": 15,
      "last_updated": "2026-04-16 12:00:00"
    }
  ],
  "current": "/path/to/project"
}
```

**后端实现**：读取 `~/.claude/webnovel-writer/workspaces.json` 注册表（已有 `project_locator.py`），遍历 `workspaces` 字典提取项目列表。每个项目的 name/genre/current_chapter 从其 `state.json` 读取。

**首次使用（注册表为空）的行为**：
- 项目切换器下拉显示"暂无项目"
- 总览页显示空状态 + "创建新小说"按钮
- 不支持"导入已有项目"（需要文件系统访问权限，浏览器环境受限）。用户只能通过创建向导新建项目
- 服务端启动时可通过命令行参数 `--project-root` 指定已有项目目录，注册到 workspaces.json

#### 3. 切换项目 `POST /api/project/switch`

项目切换器选中后调用。

**请求体**：
```json
{ "path": "/path/to/other/project" }
```

**响应**：
```json
{ "success": true, "project_root": "/path/to/other/project" }
```

**后端实现**：
1. 校验目标路径下存在 `.webnovel/state.json`
2. 更新 `_project_root` 全局变量
3. 停止旧 FileWatcher，重新启动（监控新项目的 `.webnovel/` 目录）
4. 更新 `~/.claude/webnovel-writer/workspaces.json` 中的 `last_used_project_root`
5. 前端收到成功响应后，刷新所有页面数据（项目信息、文件树、实体列表、章节列表等全部重新请求）

#### 4. 题材选项 `GET /api/genres`

创建向导第1步的题材标签数据源。

**响应**：
```json
{
  "genres": [
    { "key": "xuanhuan", "label": "修仙", "template": "修仙.md", "profile_id": "xianxia" },
    { "key": "dog-blood-romance", "label": "狗血言情", "template": "狗血言情.md", "profile_id": "romance" },
    { "key": "rules-mystery", "label": "规则怪谈", "template": "规则怪谈.md", "profile_id": "rules-mystery" },
    { "key": "zhihu-short", "label": "知乎短篇", "template": "知乎短篇.md", "profile_id": "zhihu-short" },
    { "key": "period-drama", "label": "古言", "template": "古言.md", "profile_id": "history-travel" },
    { "key": "realistic", "label": "现实题材", "template": "现实题材.md", "profile_id": null }
  ]
}
```

**后端实现**：读取两个数据源并合并：
1. `webnovel-writer/genres/` 子目录名 → 作为 `key`（唯一标识符）
2. `webnovel-writer/templates/genres/` .md 文件名 → 作为 `template`（初始化模板），其文件名即为中文显示名 `label`
3. `webnovel-writer/references/genre-profiles.md` 中的 ID → 作为 `profile_id`（追读力配置），部分题材无对应 profile 则为 `null`

**映射不一致处理**：genres/ 子目录名（如 `xuanhuan`）和 genre-profiles.md 的 ID（如 `xianxia`）存在命名差异。API 返回三个字段（key/template/profile_id）显式关联，前端只使用 `key` 作为题材标识，`label` 作为显示名。后端在 `init_project` 调用时通过 `_normalize_genre_key()` 和 `_split_genre_keys()` 进行别名转换，与现有 CLI 行为一致。

#### 5. 金手指类型 `GET /api/golden-finger-types`

创建向导第2步的金手指选项数据源。

**响应**：
```json
{
  "types": [
    { "key": "system", "label": "系统面板流" },
    { "key": "space", "label": "随身空间流" },
    { "key": "rebirth", "label": "重生/穿越流" },
    { "key": "checkin", "label": "签到打卡流" },
    { "key": "spirit", "label": "老爷爷/器灵流" },
    { "key": "bloodline", "label": "血脉/天赋型" },
    { "key": "ability", "label": "异能觉醒型" },
    { "key": "none", "label": "无金手指" }
  ]
}
```

**后端实现**：解析 `templates/golden-finger-templates.md` 中的类型标题，提取类型列表。

#### 6. 最近动态 `GET /api/recent-activity`

总览页"最近动态"时间线数据源。聚合任务执行记录 + 文件修改事件。

**响应**：
```json
{
  "activities": [
    {
      "id": "act_1",
      "type": "task_completed",
      "description": "第3章写作完成",
      "timestamp": "2026-04-16T14:30:00Z",
      "meta": { "task_type": "write_chapter", "chapter": 3 }
    },
    {
      "id": "act_2",
      "type": "file_modified",
      "description": "修改了 设定集/主角卡.md",
      "timestamp": "2026-04-16T13:15:00Z",
      "meta": { "file": "设定集/主角卡.md" }
    }
  ]
}
```

**后端实现**：聚合 `TaskService._tasks` 中的已完成任务 + SSE 中的文件变更事件。内存缓存最近 N 条（如 50 条），重启后清空。

#### 7. 大纲树 `GET /api/outline/tree`

大纲页专用结构化数据。

**实际目录结构**：`init_project.py` 创建的大纲目录是平铺结构，非子目录：
- `大纲/总纲.md` — 初始化时生成
- `大纲/爽点规划.md` — 初始化时生成
- `大纲/第1卷-详细大纲.md` — 运行时由 AI 规划生成（平铺文件，非子目录）

总纲文件内部用 Markdown 标题（`### 第1卷（第1-50章）`）组织卷结构，但文件系统不建子目录。

**响应**：
```json
{
  "files": [
    { "name": "总纲.md", "path": "大纲/总纲.md", "type": "file" },
    { "name": "爽点规划.md", "path": "大纲/爽点规划.md", "type": "file" },
    { "name": "第1卷-详细大纲.md", "path": "大纲/第1卷-详细大纲.md", "type": "file" }
  ],
  "volumes": [
    {
      "number": 1,
      "has_outline": true,
      "outline_path": "大纲/第1卷-详细大纲.md",
      "chapter_range": [1, 50]
    },
    {
      "number": 2,
      "has_outline": false,
      "outline_path": null,
      "chapter_range": [51, 100]
    }
  ],
  "total_volumes": 12
}
```

**前端渲染策略**：前端根据 `volumes` 数组构建左侧树形视图：
- 根节点：总纲（点击打开 `大纲/总纲.md`）
- 第N卷节点：
  - `has_outline=true` → 显示 ✓ + 卷纲文件名，点击打开对应 .md
  - `has_outline=false` → 显示"＋ 生成第N卷大纲"操作按钮
- 卷的章节范围从 `chapter_range` 获取

**后端实现**：
1. 扫描 `大纲/` 目录所有 .md 文件
2. 从 state.json 读取 `progress.volumes_planned` 和 `progress.current_volume`
3. 根据 `target_chapters` 计算每卷章节范围（每卷默认50章）
4. 匹配 `大纲/第N卷-详细大纲.md` 文件是否存在，确定 `has_outline`

### 数据流总览

```
前端页面                     API                        后端服务/数据源
─────────                   ───                        ──────────────
总览页
  项目状态判断      ←── GET /api/project/info  ←── state.json
  项目概况          ←── GET /api/workbench/summary ←── state.json + 目录扫描
  最近动态          ←── GET /api/recent-activity ←── 任务历史 + 文件变更
  下一步建议        ←── (前端根据状态计算)
  "继续设置"        ──→ 打开创建向导（前端状态）

创建向导
  题材选项          ←── GET /api/genres         ←── genres/ 目录 + 映射表
  金手指类型        ←── GET /api/golden-finger-types ←── templates/golden-finger-templates.md
  确认创建          ──→ POST /api/project/create ──→ init_project.init_project()
                                                        ↓ 创建目录 + state.json + 模板

大纲页
  树形结构          ←── GET /api/outline/tree   ←── 大纲/ 目录 + state.json
  文件内容          ←── GET /api/files/read     ←── 大纲/ 目录文件
  保存修改          ──→ POST /api/files/save    ──→ 写入文件
  "生成卷纲"        ──→ POST /api/tasks         ──→ TaskService → claude_runner

设定页
  实体列表(含分类)  ←── GET /api/entities?type= ←── index.db entities 表
  实体详情          ←── GET /api/entities/{id}  ←── index.db entities 表
  实体文件内容      ←── GET /api/files/read     ←── 设定集/ 目录文件
  保存修改          ──→ POST /api/files/save    ──→ 写入文件
  "检查冲突"        ──→ POST /api/tasks         ──→ TaskService → claude_runner

章节页
  章节列表          ←── GET /api/chapters       ←── index.db chapters 表
  章节文件内容      ←── GET /api/files/read     ←── 正文/ 目录文件
  保存修改          ──→ POST /api/files/save    ──→ 写入文件
  字数统计          ←── (前端实时计算，编辑区 onChange)
  "写第N章"         ──→ POST /api/tasks         ──→ TaskService → claude_runner
  "审查本章"        ──→ POST /api/tasks         ──→ TaskService → claude_runner

项目切换器
  项目列表          ←── GET /api/projects       ←── 项目注册表 + 指针文件
  切换项目          ──→ POST /api/project/switch ──→ 更新 _project_root + 重启 Watcher

AI 助手
  对话              ──→ POST /api/chat          ──→ workbench_service.build_chat_response()
  确认执行动作      ──→ POST /api/tasks         ──→ TaskService → claude_runner
  任务进度          ←── GET /api/events (SSE)   ←── TaskService + FileWatcher
```

### 任务执行链路（全量）

用户在前端触发一个动作（如"写第3章"）有两条交互路径：

**路径 A：直接执行**（按钮触发，跳过 chat）

适用于明确动作按钮（"写第N章"、"审查本章"、"生成卷纲"等），用户意图已明确，无需 AI 解析：

```
1. 前端：用户点击"写第N章"按钮
   ↓
2. 前端：直接调用 POST /api/tasks
   body: { action: { type: "write_chapter", label: "生成第3章", params: { chapter: 3 } }, context: { ... } }
   ↓
3. 后端：TaskService.create_task() 创建任务，后台线程执行
   ↓
4. 后端：claude_runner.run_action() 执行命令链
   ↓
5. SSE 推送任务状态 + 文件变更
   ↓
6. 前端：AI 助手显示进度，页面自动刷新
```

**路径 B：AI 对话触发**（聊天框输入，需意图解析）

适用于用户在 AI 助手中输入自然语言指令：

```
1. 前端：用户在 AI 助手输入"帮我写第3章"
   ↓
2. 前端：调用 POST /api/chat
   ↓
3. 后端：build_chat_response() 解析意图
   → 返回 suggested_actions: [{ type: "write_chapter", ... }]
   ↓
4. 前端：展示动作卡，用户确认执行
   ↓
5. 前端：调用 POST /api/tasks（同路径 A 第2步）
   ↓
6-8. 同路径 A 第3-6步
```

**两种路径的选取规则**：
- 页面上的明确按钮 → 路径 A（直接 POST /api/tasks）
- AI 助手聊天框输入 → 路径 B（先 POST /api/chat，确认后 POST /api/tasks）
- 总览页"写第N章"按钮 → 路径 A + 页面跳转（跳到章节页后自动创建任务）

当前 `claude_runner.run_action()` 只执行 preflight + extract-context，未真正调用 `/webnovel-write` 等 CLI 命令。全量对接需要：

1. **桥接 Claude Code CLI**：`claude_runner` 需能调用 `claude` CLI 的 slash command（如 `claude /webnovel-write --chapter 3`），或直接调用对应 skill 的 Python 实现
2. **流式输出**：当前任务只返回最终结果。AI 写作需要流式输出（逐字生成），需改造 TaskService 支持流式日志推送
3. **AI 对话升级**：`workbench_service.build_chat_response()` 从关键词匹配升级为 LLM 对话，需接入 Claude API

### 前端状态管理

前端需要维护的核心状态：

| 状态 | 来源 | 更新时机 |
|------|------|----------|
| 项目状态（无/未完成/就绪） | `GET /api/project/info` | 初始化 + SSE `file.changed`(state.json) |
| 当前项目路径 | `GET /api/projects` | 切换项目后 |
| 页面数据（大纲树/实体列表/章节列表） | 各页面 API | 初始化 + SSE 对应文件变更 |
| 当前编辑文件内容 | `GET /api/files/read` | 选中文件 + SSE 文件变更 |
| 编辑区脏状态 | 前端本地 | 用户输入 |
| AI 助手对话历史 | 前端本地 + `POST /api/chat` | 用户发送消息 |
| 任务执行状态 | SSE `task.updated` | 实时推送 |

**SSE 驱动刷新策略**：
- 收到 `file.changed` → 检查是否影响当前页面，按需重新请求对应 API
- 收到 `task.updated` → 更新 AI 助手中的任务进度显示
- 避免全量刷新：仅更新变更影响的部分组件

**编辑区脏状态与 SSE 文件变更冲突处理**：

当 SSE 推送 `file.changed` 事件，且该文件正是用户正在编辑的文件时：
- **用户有未保存修改（dirty=true）**：弹提示"文件已被外部修改，是否重新加载？"，提供两个选项：
  - "重新加载" — 丢弃本地修改，重新请求文件内容
  - "保留我的修改" — 保持当前编辑区内容不变
- **用户无未保存修改（dirty=false）**：静默重新加载文件内容
- 不做自动合并（复杂度高且容易出错）

### 后端改动清单

| 优先级 | 改动 | 涉及文件 | 说明 |
|--------|------|----------|------|
| P0 | 新增 `POST /api/project/create` | `app.py` + `workbench_service.py` | 创建向导核心，调用 `init_project.init_project()` |
| P0 | 新增 `GET /api/genres` | `app.py` | 读取 genres/ 目录 + 新建映射文件 |
| P0 | 新增 `GET /api/golden-finger-types` | `app.py` | 解析 golden-finger-templates.md |
| P0 | 新增 `GET /api/outline/tree` | `app.py` | 大纲页核心数据源 |
| P1 | 新增 `GET /api/projects` | `app.py` + 新建 `project_registry.py` | 项目切换器数据源 |
| P1 | 新增 `POST /api/project/switch` | `app.py` | 切换项目根目录 |
| P1 | 新增 `GET /api/recent-activity` | `app.py` | 总览页动态时间线 |
| P2 | `workbench_service.build_chat_response()` 升级 LLM | `workbench_service.py` | AI 对话从关键词到 LLM |
| P2 | `claude_runner.run_action()` 桥接 Claude Code CLI | `claude_runner.py` | 任务实际执行 |
| P2 | TaskService 流式输出 | `task_service.py` + `claude_runner.py` | AI 写作逐字推送 |

## 设计稿

交互式 mockup 保存在以下文件，可用浏览器打开查看：
- `docs/design-mockups/v4-all-pages.html` — 四页主设计 + AI 助手组件
- `docs/design-mockups/v4.1-supplements.html` — 创建向导、未完成设置态、章节空态等补充状态
