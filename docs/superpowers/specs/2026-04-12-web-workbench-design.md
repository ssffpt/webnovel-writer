# Web 小说工作台设计文档

## 目标

将当前依赖 Claude Code 命令驱动的网文创作系统，升级为面向非技术用户的单机单用户 Web 工作台。网页成为主入口，Claude Code 继续作为后台执行引擎。

## 用户画像

- 个人创作者
- 不懂命令行
- 主要在本机使用
- 需要通过可视化方式管理大纲、正文、设定，并触发 AI 写作流程

## 已确认边界

- 形态：编辑工作台型
- 生成方式：第一版继续复用 Claude Code / 现有 Skills 做生成
- 交互模式：聊天 + 明确按钮并存
- 部署形态：单机单用户

## 产品定位

这不是开发者仪表盘，而是 AI 辅助网文创作工作台。

核心原则：

1. 一切围绕书项目组织
2. 一切围绕当前创作任务组织
3. 用户说人话，不接触命令
4. AI 是助手，不是黑盒
5. 高成本或高风险动作需要明确确认

## 方案对比

### 方案 A：薄前端 + 后端任务代理层（推荐）

网页负责 UI；后端负责：
- 调 Claude Code 命令
- 管理任务状态
- 读写项目文件
- 推送日志与结果

优点：复用现有结构最多、改动风险最低、最快形成可用版本。

### 方案 B：前端直连本地命令/脚本

不推荐。浏览器权限、稳定性、安全性、维护性都较差。

### 方案 C：完整 Web-native 写作系统

不作为第一版。成本高，复用现有 Claude Code 链路最少。

## 总体架构

```text
Web UI
  ↓
Workbench Backend
  ├─ 项目文件服务（大纲/正文/设定）
  ├─ 任务调度服务（plan/write/review/learn）
  ├─ 聊天编排服务（自然语言 → 动作）
  ├─ Claude Code 调用适配器
  └─ 事件流/日志推送
  ↓
现有 webnovel skills + agents + data layer
```

## 页面体验方案

### 总体布局

采用三栏式工作台：

- 左侧：导航 / 书籍结构
- 中间：当前工作区
- 右侧：AI 助手 + 任务面板

原因：创作时用户会同时关心当前章节、大纲、设定、AI 建议和任务进度，三栏比多页面来回跳更顺手。

### 核心视图

#### 1. 首页 / 项目总览

展示：
- 当前项目概况
- 创作进度
- 最近任务
- 最近修改
- AI 下一步建议

作用：让用户一进来就知道现在该干什么。

#### 2. 大纲工作区

管理：
- 总纲
- 卷纲
- 章节纲

交互：
- 左侧层级树
- 中间编辑区
- 右侧 AI 操作（补全、拆分、审查、补冲突、补伏笔）

#### 3. 章节工作区

围绕单章完成写作闭环：
- 正文编辑
- 一键按大纲生成
- 续写 / 重写 / 润色 / 审查
- 展示最近一次生成结果与审查反馈

#### 4. 设定工作区

管理：
- 人物
- 势力
- 地点
- 世界观 / 体系
- 伏笔 / 债务 / 关系

体验目标：像小说资料库，而不是纯数据表。

#### 5. 聊天助手 / 创作指挥台

职责：
- 接收自然语言需求
- 理解用户意图
- 输出建议动作
- 生成动作卡供用户确认执行

原则：聊天负责理解与建议，按钮负责执行。

## 统一交互模型

所有 AI 交互统一为三步：

1. 用户表达意图（聊天 / 按钮 / 快捷菜单）
2. 系统生成动作卡（说明将执行什么、基于什么、产出什么）
3. 用户确认执行

这样可以降低误操作，并让非技术用户感到可控。

## 任务体验设计

必须有统一任务面板，展示：
- 当前任务名称
- 状态
- 步骤进度
- 用户友好日志
- 原始详细日志
- 结果 / 失败原因 / 重试

建议状态：
- 待确认
- 执行中
- 已完成
- 失败
- 已取消

## 关键用户流程

### 流程 1：从零开始写新章节

1. 用户进入章节页
2. 选择目标章节
3. 页面展示章节纲、相关设定、已有草稿状态
4. 用户点击“按大纲生成”
5. 系统弹出动作卡确认
6. 执行任务
7. 结果进入正文编辑区
8. 用户决定采纳、润色、审查或手动修改

### 流程 2：聊天驱动大纲规划

1. 用户在聊天区输入“帮我规划第二卷”
2. 系统识别为卷规划
3. 返回建议动作卡
4. 用户确认执行
5. 完成后自动跳转到大纲页并高亮新增内容

### 流程 3：修改设定后的影响检查

1. 用户在设定页修改角色或世界观
2. 系统提示受影响章节
3. 提供按钮：查看受影响章节 / 执行一致性审查 / 暂不处理

## 第一版功能范围

### 必做
- 单机启动 Web 工作台
- 打开小说项目
- 浏览并编辑大纲 / 正文 / 设定
- 聊天输入
- 从聊天生成可执行动作
- 一键触发 plan / write / review
- 实时查看任务状态与日志
- 任务完成后自动刷新相关页面

### 暂不做
- 多用户
- 登录权限
- 云同步
- 在线协作
- 高级富文本编辑器
- 全自动自治式代理

## 技术实现方向

### 前端模块
- App Shell
- Workspace Pages
- Chat Assistant
- Task Panel
- Editors
- Shared Components

### 后端模块
- Project Service
- File Service
- Task Service
- Claude Runner
- Chat Orchestrator
- Event Stream

### 关键 API
- 项目接口：打开/切换项目、读取项目状态
- 文件接口：读取、保存、新建、重命名
- 任务接口：创建、查询、取消、日志
- 聊天接口：自然语言 → 动作建议
- 实时事件接口：任务状态、日志、文件变化

## 技术风险

1. Claude Code 输出结构化程度有限，第一版不要强依赖精确解析
2. 长任务需要高可见性，任务面板优先级必须高
3. 文件格式可能不统一，第一版先做文件级编辑，不急于强结构化
4. 只读 dashboard 代码需要与可写接口、任务接口做清晰边界拆分

## 分阶段规划

### Phase 1：工作台骨架
- 新导航结构
- 大纲/正文/设定编辑器
- 保存接口
- 当前项目打开逻辑

### Phase 2：任务执行接入
- Task Service
- Claude Runner
- 任务创建与状态展示
- 日志推送

### Phase 3：聊天助手
- 聊天 UI
- `/api/chat`
- 动作卡生成
- 聊天与工作区联动

### Phase 4：体验优化
- 自动跳转
- 失败恢复
- 草稿对比
- 未保存提醒
- 受影响章节提示

## 当前建议

第一版最现实的路线是：

> 以现有 FastAPI Dashboard + 前端为底座，新增 Workbench API、任务调度层和聊天动作层，把 Claude Code 工作流包装成网页按钮和动作卡。

这条路线复用现有能力最多，最容易尽快做出真正可用的单机创作工作台。

## MVP 收缩策略

为了尽快形成可用版本，第一版进一步收缩为“少页面、先跑通主流程”的 MVP。

### MVP 页面集合

仅保留三个主工作区：

1. 章节工作台
2. 大纲工作台
3. 设定工作台

同时保留一个全局右侧栏：
- 聊天助手
- 动作卡
- 当前任务面板

### MVP 暂不做

- 首页
- 独立任务中心
- 复杂统计图表
- 富文本编辑器
- 拖拽排序
- 多标签编辑
- 自动无确认执行

### MVP 核心目标

只验证三个主流程：

1. 大纲页选章纲 → 生成章节
2. 章节页编辑正文 → 审查本章
3. 设定页修改人物/世界观 → 检查冲突

## MVP 页面原型清单

### 全局框架

统一结构：

- 顶栏：项目名 + 页面切换（章节 / 大纲 / 设定） + 当前任务状态小提示
- 左栏：当前页面的结构导航
- 中栏：当前页面的主编辑区
- 右栏：聊天 + 动作 + 当前任务

### 章节工作台

左栏：
- 章节筛选条（全部 / 未写 / 草稿 / 已审查）
- 章节列表（章节号、标题、状态点）

中栏：
- 章节头部（章节号、标题、所属卷、保存状态）
- 正文编辑器
- AI 结果摘要区（最近生成 / 审查摘要 / 风险提示）
- 底部操作条：保存 / 按大纲生成 / 审查本章

右栏：
- 当前上下文提示（当前章节、是否已有章纲、是否有未保存改动）
- 聊天区
- 动作卡区
- 当前任务卡

### 大纲工作台

左栏：
- 大纲树（总纲 / 卷纲 / 章纲）
- 新建卷/章大纲按钮

中栏：
- 当前节点头部（类型、标题、保存状态）
- 大纲编辑器
- 辅助信息区（是否已拆章、是否已有对应正文、是否建议开始写作）
- 底部操作条：保存 / 生成卷纲 / 生成章纲

右栏：
- 聊天区
- 动作卡区
- 当前任务卡

### 设定工作台

左栏：
- 分类导航（人物 / 势力 / 地点 / 世界观）
- 条目列表
- 新建条目按钮

中栏：
- 设定头部（名称、分类、保存状态）
- 设定编辑区（名称输入 + 内容编辑）
- 关联提示区（相关章节数、最近出现章节、潜在冲突）
- 底部操作条：保存 / 检查冲突

右栏：
- 聊天区
- 动作卡区
- 当前任务卡

### 右侧全局栏

#### 聊天区
- 消息列表
- 多行输入框
- 发送按钮
- 空状态提示词

#### 动作卡区
每张卡统一显示：
- 动作标题
- 简短说明
- 作用对象
- 预计结果
- 执行 / 取消按钮

#### 当前任务区
显示：
- 任务名
- 状态
- 当前步骤
- 最近更新时间
- 展开日志 / 失败重试

## MVP 技术实现拆分

### 前端结构建议

```text
frontend/src/
  App.jsx
  app-shell/
  pages/
  components/
  panels/
  editors/
  services/
  store/
```

#### 页面层
- `pages/ChapterPage.jsx`
- `pages/OutlinePage.jsx`
- `pages/SettingPage.jsx`

#### 壳层组件
- `app-shell/TopBar.jsx`
- `app-shell/LeftSidebar.jsx`
- `app-shell/MainWorkspace.jsx`
- `app-shell/RightSidebar.jsx`

#### 左侧导航组件
- `components/chapter/ChapterList.jsx`
- `components/chapter/ChapterFilter.jsx`
- `components/outline/OutlineTree.jsx`
- `components/setting/SettingCategoryList.jsx`
- `components/setting/SettingItemList.jsx`

#### 编辑组件
- `editors/ChapterEditor.jsx`
- `editors/OutlineEditor.jsx`
- `editors/SettingEditor.jsx`

#### 右侧统一组件
- `panels/ChatPanel.jsx`
- `panels/ActionPanel.jsx`
- `panels/TaskPanel.jsx`
- `panels/ContextPanel.jsx`

#### 服务层
- `services/projectApi.js`
- `services/fileApi.js`
- `services/taskApi.js`
- `services/chatApi.js`
- `services/eventApi.js`

#### 状态层
- `store/workspaceStore.js`
- `store/taskStore.js`
- `store/chatStore.js`

### 后端结构建议

在 `webnovel-writer/dashboard/` 下新增：

```text
dashboard/
  api/
  services/
  models/
  runners/
```

#### API 层
- `api/project.py`
- `api/files.py`
- `api/tasks.py`
- `api/chat.py`
- `api/events.py`

#### 服务层
- `services/project_service.py`
- `services/file_service.py`
- `services/task_service.py`
- `services/chat_service.py`

#### Runner 层
- `runners/claude_runner.py`

#### Model 层
- `models/task.py`
- `models/action.py`
- `models/file_payload.py`

### MVP 最小 API 集合

- `GET /api/project/info`
- `GET /api/files/tree`
- `GET /api/files/read`
- `POST /api/files/save`
- `POST /api/tasks`
- `GET /api/tasks/current`
- `GET /api/tasks/{id}`
- `POST /api/chat`
- `GET /api/events`

### MVP 开发顺序

#### Phase 1A：工作台 UI 骨架
- 顶栏
- 三页面切换
- 左中右三栏布局
- 右侧栏假数据渲染

#### Phase 1B：文件浏览与编辑
- 文件树 / 章节列表 / 设定分类
- 读取内容
- 编辑保存
- 脏状态提示

#### Phase 1C：聊天与动作卡壳子
- 聊天 UI
- `/api/chat` 占位或规则版实现
- 动作卡展示
- 执行按钮

#### Phase 1D：任务面板壳子
- 当前任务卡
- 任务状态
- 简单日志流

#### Phase 2：Claude 任务接入
- `claude_runner.py`
- `/api/tasks`
- 动作到现有命令/流程的映射
- 任务执行与状态回传

### MVP 最小动作集合

第一版先只接三个动作：
- `write_chapter`
- `review_chapter`
- `plan_outline`

这三个动作足以验证网页能否替代命令行完成核心创作流程。
