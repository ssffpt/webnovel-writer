# API接口规范

<cite>
**本文引用的文件**
- [webnovel-writer/dashboard/app.py](file://webnovel-writer/dashboard/app.py)
- [webnovel-writer/dashboard/server.py](file://webnovel-writer/dashboard/server.py)
- [webnovel-writer/dashboard/task_service.py](file://webnovel-writer/dashboard/task_service.py)
- [webnovel-writer/dashboard/workbench_service.py](file://webnovel-writer/dashboard/workbench_service.py)
- [webnovel-writer/dashboard/models.py](file://webnovel-writer/dashboard/models.py)
- [webnovel-writer/dashboard/path_guard.py](file://webnovel-writer/dashboard/path_guard.py)
- [webnovel-writer/dashboard/watcher.py](file://webnovel-writer/dashboard/watcher.py)
- [webnovel-writer/dashboard/frontend/src/api.js](file://webnovel-writer/dashboard/frontend/src/api.js)
- [webnovel-writer/scripts/data_modules/api_client.py](file://webnovel-writer/scripts/data_modules/api_client.py)
- [webnovel-writer/dashboard/genre_service.py](file://webnovel-writer/dashboard/genre_service.py)
- [webnovel-writer/dashboard/project_service.py](file://webnovel-writer/dashboard/project_service.py)
- [webnovel-writer/dashboard/tests/test_new_apis.py](file://webnovel-writer/dashboard/tests/test_new_apis.py)
</cite>

## 更新摘要
**变更内容**
- 新增题材与金手指相关API：GET /api/genres、GET /api/golden-finger-types
- 新增项目管理相关API：POST /api/project/create、GET /api/projects、POST /api/project/switch
- 新增大纲树与最近活动相关API：GET /api/outline/tree、GET /api/recent-activity
- 新增对应的后端服务模块：genre_service.py、project_service.py
- 更新前端API工具：新增对应的数据获取函数

## 目录
1. [简介](#简介)
2. [项目结构](#项目结构)
3. [核心组件](#核心组件)
4. [架构总览](#架构总览)
5. [详细组件分析](#详细组件分析)
6. [依赖关系分析](#依赖关系分析)
7. [性能考虑](#性能考虑)
8. [故障排查指南](#故障排查指南)
9. [结论](#结论)
10. [附录](#附录)

## 简介
本文件为 Webnovel Writer 的 Web 工作台 API 接口规范参考文档，覆盖以下能力：
- 项目信息查询：返回工作台所需的基础项目信息与进度概览
- 实体数据库查询：对只读索引数据库 index.db 的统一查询接口
- 文件操作：树形目录浏览、只读读取、安全写入
- 任务管理：创建任务、查询任务、当前任务状态
- 聊天交互：基于自然语言的意图识别与建议动作
- 实时事件推送：文件变更与任务状态的 SSE 推送
- **新增** 题材与金手指管理：获取题材列表、金手指类型、项目创建与切换
- **新增** 大纲树与活动追踪：构建大纲树结构、获取最近活动记录

同时，文档阐述认证机制（无内置认证）、错误处理策略、数据验证规则、版本兼容性与使用场景，并提供请求/响应示例、状态码说明、集成指南与测试用例。

## 项目结构
Web 工作台后端采用 FastAPI，提供 RESTful API 与 SSE；前端通过 EventSource 订阅实时事件；文件系统访问通过路径守卫进行安全校验；任务执行通过线程池异步调度；新增的题材与项目管理功能通过专门的服务模块提供。

```mermaid
graph TB
subgraph "后端"
A["FastAPI 应用<br/>app.py"]
B["任务服务<br/>task_service.py"]
C["文件监听器<br/>watcher.py"]
D["工作台辅助<br/>workbench_service.py"]
E["常量与模型<br/>models.py"]
F["路径守卫<br/>path_guard.py"]
G["题材服务<br/>genre_service.py"]
H["项目服务<br/>project_service.py"]
end
subgraph "前端"
I["API 工具<br/>frontend/src/api.js"]
end
subgraph "外部"
J["SQLite 数据库<br/>index.db"]
K["项目文件系统<br/>正文/大纲/设定集"]
L["工作空间注册表<br/>workspaces.json"]
end
I --> A
A --> D
A --> B
A --> C
A --> F
A --> G
A --> H
A --> J
A --> K
A --> L
```

**图表来源**
- [webnovel-writer/dashboard/app.py:50-489](file://webnovel-writer/dashboard/app.py#L50-L489)
- [webnovel-writer/dashboard/task_service.py:14-166](file://webnovel-writer/dashboard/task_service.py#L14-L166)
- [webnovel-writer/dashboard/watcher.py:40-95](file://webnovel-writer/dashboard/watcher.py#L40-L95)
- [webnovel-writer/dashboard/workbench_service.py:18-55](file://webnovel-writer/dashboard/workbench_service.py#L18-L55)
- [webnovel-writer/dashboard/models.py:3-22](file://webnovel-writer/dashboard/models.py#L3-L22)
- [webnovel-writer/dashboard/path_guard.py:11-28](file://webnovel-writer/dashboard/path_guard.py#L11-L28)
- [webnovel-writer/dashboard/genre_service.py:1-152](file://webnovel-writer/dashboard/genre_service.py#L1-L152)
- [webnovel-writer/dashboard/project_service.py:1-181](file://webnovel-writer/dashboard/project_service.py#L1-L181)
- [webnovel-writer/dashboard/frontend/src/api.js:1-78](file://webnovel-writer/dashboard/frontend/src/api.js#L1-L78)

**章节来源**
- [webnovel-writer/dashboard/app.py:50-489](file://webnovel-writer/dashboard/app.py#L50-L489)
- [webnovel-writer/dashboard/server.py:43-72](file://webnovel-writer/dashboard/server.py#L43-L72)

## 核心组件
- FastAPI 应用：集中定义所有 REST API 与 SSE 端点，负责路由、中间件与生命周期管理
- 任务服务：维护任务队列、状态机与事件分发，支持并发订阅
- 文件监听器：监控 .webnovel 关键文件变更并通过 SSE 推送
- 工作台辅助：汇总项目摘要、执行安全文件写入与聊天意图识别
- 路径守卫：防止路径穿越，限定文件访问范围
- 前端 API 工具：封装 GET/POST 与 SSE 订阅
- **新增** 题材服务：提供题材列表与金手指类型解析
- **新增** 项目服务：提供项目创建、列表与切换功能

**章节来源**
- [webnovel-writer/dashboard/app.py:50-489](file://webnovel-writer/dashboard/app.py#L50-L489)
- [webnovel-writer/dashboard/task_service.py:14-166](file://webnovel-writer/dashboard/task_service.py#L14-L166)
- [webnovel-writer/dashboard/watcher.py:40-95](file://webnovel-writer/dashboard/watcher.py#L40-L95)
- [webnovel-writer/dashboard/workbench_service.py:18-171](file://webnovel-writer/dashboard/workbench_service.py#L18-L171)
- [webnovel-writer/dashboard/path_guard.py:11-28](file://webnovel-writer/dashboard/path_guard.py#L11-L28)
- [webnovel-writer/dashboard/models.py:3-22](file://webnovel-writer/dashboard/models.py#L3-L22)
- [webnovel-writer/dashboard/frontend/src/api.js:1-78](file://webnovel-writer/dashboard/frontend/src/api.js#L1-L78)
- [webnovel-writer/dashboard/genre_service.py:1-152](file://webnovel-writer/dashboard/genre_service.py#L1-L152)
- [webnovel-writer/dashboard/project_service.py:1-181](file://webnovel-writer/dashboard/project_service.py#L1-L181)

## 架构总览
后端通过 FastAPI 提供统一入口，实体数据库查询走只读路径，文件读写受路径守卫约束，任务执行与文件变更通过事件总线推送至前端。新增的题材与项目管理功能通过专门的服务模块提供，与主应用解耦。

```mermaid
sequenceDiagram
participant FE as "前端"
participant API as "FastAPI 应用"
participant WB as "工作台辅助"
participant TS as "任务服务"
participant FW as "文件监听器"
participant GS as "题材服务"
participant PS as "项目服务"
FE->>API : "GET /api/project/info"
API-->>FE : "项目基础信息"
FE->>API : "GET /api/workbench/summary"
API->>WB : "load_project_summary()"
WB-->>API : "工作台摘要"
API-->>FE : "工作台摘要"
FE->>API : "GET /api/genres"
API->>GS : "list_genres()"
GS-->>API : "题材列表"
API-->>FE : "题材列表"
FE->>API : "GET /api/golden-finger-types"
API->>GS : "list_golden_finger_types()"
GS-->>API : "金手指类型"
API-->>FE : "金手指类型"
FE->>API : "POST /api/project/create"
API->>PS : "create_project()"
PS-->>API : "创建结果"
API-->>FE : "创建结果"
FE->>API : "GET /api/projects"
API->>PS : "list_projects()"
PS-->>API : "项目列表"
API-->>FE : "项目列表"
FE->>API : "GET /api/outline/tree"
API->>WB : "build_outline_tree()"
WB-->>API : "大纲树结构"
API-->>FE : "大纲树结构"
FE->>API : "GET /api/recent-activity"
API-->>FE : "最近活动"
FE->>API : "GET /api/entities?type=...&include_archived=..."
API-->>FE : "实体列表"
FE->>API : "GET /api/files/tree"
API-->>FE : "文件树"
FE->>API : "GET /api/files/read?path=..."
API->>FW : "安全解析与校验"
API-->>FE : "文件内容"
FE->>API : "POST /api/files/save"
API->>FW : "安全解析与校验"
API-->>FE : "保存结果"
FE->>API : "POST /api/tasks"
API->>TS : "创建任务"
TS-->>API : "任务快照"
API-->>FE : "任务ID与初始状态"
FE->>API : "GET /api/tasks/current"
API->>TS : "查询当前任务"
TS-->>API : "当前任务"
API-->>FE : "当前任务"
FE->>API : "GET /api/tasks/{id}"
API->>TS : "查询指定任务"
TS-->>API : "任务详情"
API-->>FE : "任务详情"
FE->>API : "POST /api/chat"
API->>WB : "build_chat_response()"
WB-->>API : "建议动作与回复"
API-->>FE : "聊天响应"
FE->>API : "GET /api/events"
API->>FW : "订阅文件事件"
API->>TS : "订阅任务事件"
FW-->>API : "文件变更事件"
TS-->>API : "任务状态事件"
API-->>FE : "SSE 流"
```

**图表来源**
- [webnovel-writer/dashboard/app.py:80-461](file://webnovel-writer/dashboard/app.py#L80-L461)
- [webnovel-writer/dashboard/workbench_service.py:74-162](file://webnovel-writer/dashboard/workbench_service.py#L74-L162)
- [webnovel-writer/dashboard/task_service.py:36-120](file://webnovel-writer/dashboard/task_service.py#L36-L120)
- [webnovel-writer/dashboard/watcher.py:63-77](file://webnovel-writer/dashboard/watcher.py#L63-L77)
- [webnovel-writer/dashboard/frontend/src/api.js:61-77](file://webnovel-writer/dashboard/frontend/src/api.js#L61-L77)
- [webnovel-writer/dashboard/genre_service.py:37-151](file://webnovel-writer/dashboard/genre_service.py#L37-L151)
- [webnovel-writer/dashboard/project_service.py:81-181](file://webnovel-writer/dashboard/project_service.py#L81-L181)

## 详细组件分析

### 项目信息与工作台摘要
- 端点
  - GET /api/project/info：返回 .webnovel/state.json 的完整内容（只读）
  - GET /api/workbench/summary：聚合项目标题、体裁、目标字数/章节数、进度与工作区统计
- 请求参数
  - 无
- 响应格式
  - 返回 JSON 对象，包含 pages、project、progress、workspace_roots、workspaces 等字段
- 使用场景
  - 初始化工作台界面、展示项目概览与进度

**章节来源**
- [webnovel-writer/dashboard/app.py:80-91](file://webnovel-writer/dashboard/app.py#L80-L91)
- [webnovel-writer/dashboard/workbench_service.py:18-55](file://webnovel-writer/dashboard/workbench_service.py#L18-L55)

### 实体数据库查询（index.db 只读）
- 端点
  - GET /api/entities：列出实体，支持按类型过滤与是否包含归档
  - GET /api/entities/{entity_id}：按 ID 查询实体
  - GET /api/relationships：按实体或全局查询关系，支持限制条数
  - GET /api/relationship-events：按实体与章节区间查询关系事件
  - GET /api/chapters：查询全部章节
  - GET /api/scenes：按章节或全局查询场景
  - GET /api/reading-power：查询阅读力指标
  - GET /api/review-metrics：查询评审指标
  - GET /api/state-changes：按实体或全局查询状态变更
  - GET /api/aliases：按实体或全局查询别名
  - GET /api/overrides、/api/debts、/api/debt-events、/api/invalid-facts、/api/rag-queries、/api/tool-stats、/api/checklist-scores：扩展表查询（v5.3+/v5.4+），支持状态过滤与限制条数
- 请求参数
  - 除路径参数外，多数端点支持 limit、status、entity、from_chapter、to_chapter 等查询参数
- 响应格式
  - 返回 JSON 数组或对象，字段与表结构一致
- 错误处理
  - index.db 不存在返回 404；表不存在时返回空数组（扩展表）
- 版本兼容性
  - 扩展表仅在 v5.3+ 或 v5.4+ 存在时可用

**章节来源**
- [webnovel-writer/dashboard/app.py:114-347](file://webnovel-writer/dashboard/app.py#L114-L347)

### 文件操作（只读浏览、安全读取、写入）
- 端点
  - GET /api/files/tree：返回"正文/大纲/设定集"三类目录树
  - GET /api/files/read：只读读取文件内容，路径受安全校验
  - POST /api/files/save：安全写入文件，仅允许写入三大目录
- 请求参数
  - read：path（字符串）
  - save：payload 包含 path、content（均为字符串）
- 响应格式
  - tree：返回各目录的树形结构
  - read：返回 { path, content }
  - save：返回 { path, saved_at, size }
- 安全机制
  - 所有文件访问均通过路径守卫校验，禁止逃逸 PROJECT_ROOT
  - 仅允许读取/写入"正文/大纲/设定集"目录
- 使用场景
  - 展示与编辑正文、大纲、设定集文件

**章节来源**
- [webnovel-writer/dashboard/app.py:352-394](file://webnovel-writer/dashboard/app.py#L352-L394)
- [webnovel-writer/dashboard/path_guard.py:11-28](file://webnovel-writer/dashboard/path_guard.py#L11-L28)
- [webnovel-writer/dashboard/workbench_service.py:58-71](file://webnovel-writer/dashboard/workbench_service.py#L58-L71)

### 任务管理
- 端点
  - GET /api/tasks/current：查询当前任务
  - POST /api/tasks：创建任务，合并上下文并注入项目根路径
  - GET /api/tasks/{task_id}：查询指定任务
- 请求参数
  - POST /api/tasks：payload 包含 action（对象，必填）与 context（对象，可选）
- 响应格式
  - 创建任务返回任务快照（包含 id、status、action、context、时间戳、日志、结果/错误）
  - 查询任务返回完整任务对象
- 任务状态
  - idle、pending、running、completed、failed、cancelled（部分状态）
- 使用场景
  - 异步执行规划、审查、写作、设定检查等动作

```mermaid
stateDiagram-v2
[*] --> 空闲
空闲 --> 待定 : "创建任务"
待定 --> 运行中 : "标记运行"
运行中 --> 成功 : "标记完成"
运行中 --> 失败 : "标记失败"
成功 --> 空闲 : "清理/复用"
失败 --> 空闲 : "清理/复用"
```

**图表来源**
- [webnovel-writer/dashboard/models.py:9-22](file://webnovel-writer/dashboard/models.py#L9-L22)
- [webnovel-writer/dashboard/task_service.py:66-120](file://webnovel-writer/dashboard/task_service.py#L66-L120)

**章节来源**
- [webnovel-writer/dashboard/app.py:395-419](file://webnovel-writer/dashboard/app.py#L395-L419)
- [webnovel-writer/dashboard/task_service.py:14-166](file://webnovel-writer/dashboard/task_service.py#L14-L166)
- [webnovel-writer/dashboard/models.py:3-22](file://webnovel-writer/dashboard/models.py#L3-L22)

### 聊天交互
- 端点
  - POST /api/chat：根据用户消息与上下文生成建议动作
- 请求参数
  - payload 包含 message（字符串，必填）与 context（对象，可选）
- 响应格式
  - 返回 { reply, suggested_actions, reason, scope }
  - 若检测到未保存修改，返回安全提示与建议动作列表
- 使用场景
  - 通过自然语言触发大纲规划、设定检查、章节审查、章节写作等动作

```mermaid
flowchart TD
Start(["收到聊天请求"]) --> Parse["解析 message 与 context"]
Parse --> Dirty{"存在未保存修改？"}
Dirty --> |是| Warn["返回安全提示与建议动作"]
Dirty --> |否| Classify["关键词分类"]
Classify --> Plan{"是否为大纲规划？"}
Plan --> |是| ActionPlan["生成大纲规划动作"]
Plan --> |否| Setting{"是否为设定检查？"}
Setting --> |是| ActionSetting["生成设定检查动作"]
Setting --> |否| Review{"是否为章节审查？"}
Review --> |是| ActionReview["生成章节审查动作"]
Review --> |否| Write{"是否为章节写作？"}
Write --> |是| ActionWrite["生成章节写作动作"]
Write --> |否| Continue{"是否为继续？"}
Continue --> |是| PageType{"当前页面类型？"}
PageType --> Outline["优先大纲规划动作"]
PageType --> Chapters["优先章节写作动作"]
PageType --> Settings["优先设定检查动作"]
Continue --> |否| NoAction["无匹配动作"]
ActionPlan --> Reply["组装回复与建议动作"]
ActionSetting --> Reply
ActionReview --> Reply
ActionWrite --> Reply
Outline --> Reply
Chapters --> Reply
Settings --> Reply
NoAction --> Reply
Warn --> End(["返回响应"])
Reply --> End
```

**图表来源**
- [webnovel-writer/dashboard/workbench_service.py:74-162](file://webnovel-writer/dashboard/workbench_service.py#L74-L162)

**章节来源**
- [webnovel-writer/dashboard/app.py:420-429](file://webnovel-writer/dashboard/app.py#L420-L429)
- [webnovel-writer/dashboard/workbench_service.py:74-162](file://webnovel-writer/dashboard/workbench_service.py#L74-L162)

### 实时事件推送（SSE）
- 端点
  - GET /api/events：Server-Sent Events，推送文件变更与任务状态
- 事件类型
  - file.changed：文件变更事件，包含文件名、变更类型与时间戳
  - task.updated：任务状态更新事件，包含任务ID与任务快照
- 使用场景
  - 前端自动刷新数据、跟踪任务执行进度

```mermaid
sequenceDiagram
participant FE as "前端"
participant API as "FastAPI 应用"
participant FW as "文件监听器"
participant TS as "任务服务"
FE->>API : "GET /api/events"
API->>FW : "subscribe()"
API->>TS : "subscribe_events()"
FW-->>API : "file.changed"
TS-->>API : "task.updated"
API-->>FE : "SSE data : {...}"
FE-->>API : "断开/重连"
API->>FW : "unsubscribe()"
API->>TS : "unsubscribe_events()"
```

**图表来源**
- [webnovel-writer/dashboard/app.py:434-461](file://webnovel-writer/dashboard/app.py#L434-L461)
- [webnovel-writer/dashboard/watcher.py:50-77](file://webnovel-writer/dashboard/watcher.py#L50-L77)
- [webnovel-writer/dashboard/task_service.py:25-34](file://webnovel-writer/dashboard/task_service.py#L25-L34)

**章节来源**
- [webnovel-writer/dashboard/app.py:434-461](file://webnovel-writer/dashboard/app.py#L434-L461)
- [webnovel-writer/dashboard/watcher.py:40-95](file://webnovel-writer/dashboard/watcher.py#L40-L95)
- [webnovel-writer/dashboard/task_service.py:14-166](file://webnovel-writer/dashboard/task_service.py#L14-L166)

### **新增** 题材与金手指管理

#### 题材列表获取
- 端点
  - GET /api/genres：返回可用题材列表
- 请求参数
  - 无
- 响应格式
  - 返回 JSON 对象，包含 genres 数组
  - 每个题材项包含 key（英文标识符）、label（中文显示名）、template（模板文件名）、profile_id（可选）
- 数据来源
  - templates/genres/*.md：37个中文题材显示名与模板
  - genres/ 子目录：6个核心题材的英文标识符
  - references/genre-profiles.md：13个追读力配置ID
- 使用场景
  - 创建项目时选择题材、显示题材列表

**章节来源**
- [webnovel-writer/dashboard/app.py:124-130](file://webnovel-writer/dashboard/app.py#L124-L130)
- [webnovel-writer/dashboard/genre_service.py:37-93](file://webnovel-writer/dashboard/genre_service.py#L37-L93)

#### 金手指类型获取
- 端点
  - GET /api/golden-finger-types：返回金手指类型列表
- 请求参数
  - 无
- 响应格式
  - 返回 JSON 对象，包含 types 数组
  - 每个类型项包含 key（英文标识符）与 label（中文显示名）
  - 始终包含 key='none' 的"无金手指"选项
- 数据来源
  - templates/golden-finger-templates.md：金手指类型定义
- 使用场景
  - 创建项目时选择金手指类型、显示类型列表

**章节来源**
- [webnovel-writer/dashboard/app.py:128-130](file://webnovel-writer/dashboard/app.py#L128-L130)
- [webnovel-writer/dashboard/genre_service.py:109-151](file://webnovel-writer/dashboard/genre_service.py#L109-L151)

### **新增** 项目管理功能

#### 项目创建
- 端点
  - POST /api/project/create：创建新项目
- 请求参数
  - payload 包含 title（必需，字符串）、genre（可选）、protagonist_name（可选）、target_words（可选）、target_chapters（可选）、golden_finger_name（可选）、golden_finger_type（可选）、core_selling_points（可选）
- 响应格式
  - 返回 JSON 对象，包含 success（布尔）、project_root（字符串）、state（对象或null）
- 错误处理
  - title 缺失或为空时返回 400
  - 创建失败时返回 400，包含 error 信息
- 使用场景
  - 通过创建向导初始化新项目

**章节来源**
- [webnovel-writer/dashboard/app.py:136-147](file://webnovel-writer/dashboard/app.py#L136-L147)
- [webnovel-writer/dashboard/project_service.py:81-136](file://webnovel-writer/dashboard/project_service.py#L81-L136)

#### 项目列表获取
- 端点
  - GET /api/projects：返回已注册项目列表
- 请求参数
  - 无
- 响应格式
  - 返回 JSON 对象，包含 projects（数组）与 current（当前项目路径）
  - projects 数组中每个项目包含 name、path、genre、current_chapter、last_updated
- 数据来源
  - ~/.claude/webnovel-writer/workspaces.json：项目注册表
- 使用场景
  - 显示项目历史、选择最近使用的项目

**章节来源**
- [webnovel-writer/dashboard/app.py:149-151](file://webnovel-writer/dashboard/app.py#L149-L151)
- [webnovel-writer/dashboard/project_service.py:139-167](file://webnovel-writer/dashboard/project_service.py#L139-L167)

#### 项目切换
- 端点
  - POST /api/project/switch：切换到目标项目
- 请求参数
  - payload 包含 path（目标项目路径）
- 响应格式
  - 返回 JSON 对象，包含 success（布尔）与 project_root（字符串）
- 错误处理
  - 目标路径不是有效项目时返回 400
- 使用场景
  - 在多个项目间快速切换

**章节来源**
- [webnovel-writer/dashboard/app.py:153-162](file://webnovel-writer/dashboard/app.py#L153-L162)
- [webnovel-writer/dashboard/project_service.py:170-181](file://webnovel-writer/dashboard/project_service.py#L170-L181)

### **新增** 大纲树与活动追踪

#### 大纲树结构获取
- 端点
  - GET /api/outline/tree：构建并返回大纲树结构
- 请求参数
  - 无
- 响应格式
  - 返回 JSON 对象，包含 files（文件列表）、volumes（卷信息）、total_volumes（总卷数）
  - files：大纲目录下所有.md文件的名称、路径与类型
  - volumes：按目标章节数计算的卷信息，包含 number、has_outline、outline_path、chapter_range
- 计算逻辑
  - 每卷50章，基于项目目标章节数计算总卷数
  - 检测是否存在"第N卷-详细大纲.md"文件
- 使用场景
  - 大纲页面导航、卷级规划

**章节来源**
- [webnovel-writer/dashboard/app.py:168-170](file://webnovel-writer/dashboard/app.py#L168-L170)
- [webnovel-writer/dashboard/workbench_service.py:174-238](file://webnovel-writer/dashboard/workbench_service.py#L174-L238)

#### 最近活动获取
- 端点
  - GET /api/recent-activity：返回最近的活动记录
- 请求参数
  - 无
- 响应格式
  - 返回 JSON 对象，包含 activities（数组，最多50条）
- 数据来源
  - 内存中的 _recent_activities 列表
- 使用场景
  - 显示项目活动历史、跟踪操作记录

**章节来源**
- [webnovel-writer/dashboard/app.py:172-174](file://webnovel-writer/dashboard/app.py#L172-L174)

## 依赖关系分析
- 组件耦合
  - app.py 作为入口，依赖工作台辅助、任务服务、文件监听器、路径守卫、题材服务与项目服务
  - 任务服务与文件监听器通过事件队列与异步循环解耦
  - 新增的 genre_service.py 与 project_service.py 作为独立服务模块
- 外部依赖
  - SQLite：index.db 只读查询
  - watchdog：文件系统事件监听
  - FastAPI：路由与中间件
  - 前端 EventSource：SSE 客户端
  - **新增** 子进程：用于项目初始化脚本执行

```mermaid
graph LR
APP["app.py"] --> WB["workbench_service.py"]
APP --> TS["task_service.py"]
APP --> FW["watcher.py"]
APP --> PG["path_guard.py"]
APP --> GS["genre_service.py"]
APP --> PS["project_service.py"]
APP --> DB["index.db"]
FE["frontend/api.js"] --> APP
```

**图表来源**
- [webnovel-writer/dashboard/app.py:20-24](file://webnovel-writer/dashboard/app.py#L20-L24)
- [webnovel-writer/dashboard/task_service.py:10-11](file://webnovel-writer/dashboard/task_service.py#L10-L11)
- [webnovel-writer/dashboard/watcher.py:14-15](file://webnovel-writer/dashboard/watcher.py#L14-L15)
- [webnovel-writer/dashboard/frontend/src/api.js:61-77](file://webnovel-writer/dashboard/frontend/src/api.js#L61-L77)
- [webnovel-writer/dashboard/genre_service.py:1-152](file://webnovel-writer/dashboard/genre_service.py#L1-L152)
- [webnovel-writer/dashboard/project_service.py:1-181](file://webnovel-writer/dashboard/project_service.py#L1-L181)

**章节来源**
- [webnovel-writer/dashboard/app.py:20-24](file://webnovel-writer/dashboard/app.py#L20-L24)

## 性能考虑
- 并发与限流
  - 任务服务使用线程池与锁保证并发安全，最大订阅队列容量控制内存占用
  - SSE 订阅队列设置上限，超限自动移除死订阅
  - **新增** 题材与项目服务采用轻量级数据解析，避免复杂计算
- I/O 优化
  - 实体查询统一走只读连接，Row 工厂便于序列化
  - 文件读取对二进制文件返回占位信息，避免大文件阻塞
  - **新增** 项目注册表直接读取 JSON 文件，避免复杂依赖
- 网络与缓存
  - SSE 自动重连，前端无需手动处理断线
  - 建议前端对高频查询做本地缓存与去抖
  - **新增** 最近活动列表限制在50条以内，控制响应大小

## 故障排查指南
- 404：index.db 或 state.json 不存在
  - 检查 .webnovel 目录完整性
- 404：文件不存在或路径越界
  - 确认路径在"正文/大纲/设定集"范围内，使用安全解析
- 403：路径越界或禁止写入
  - 禁止访问 PROJECT_ROOT 之外的文件；仅允许写入三大目录
- 400：请求体参数类型错误
  - 确保 message、path、content 为字符串，action/context 为对象
  - **新增** 创建项目时 title 必须为非空字符串
- **新增** 400：项目创建失败
  - 检查 init_project.py 脚本执行结果，确认参数格式正确
- **新增** 400：项目切换失败
  - 确认目标路径包含有效的 .webnovel/state.json 文件
- SSE 不接收事件
  - 检查浏览器网络面板与 EventSource 连接状态，确认后端未关闭队列

**章节来源**
- [webnovel-writer/dashboard/app.py:84-86](file://webnovel-writer/dashboard/app.py#L84-L86)
- [webnovel-writer/dashboard/app.py:96-102](file://webnovel-writer/dashboard/app.py#L96-L102)
- [webnovel-writer/dashboard/app.py:376-377](file://webnovel-writer/dashboard/app.py#L376-L377)
- [webnovel-writer/dashboard/app.py:388-393](file://webnovel-writer/dashboard/app.py#L388-L393)
- [webnovel-writer/dashboard/app.py:403-406](file://webnovel-writer/dashboard/app.py#L403-L406)
- [webnovel-writer/dashboard/app.py:139-141](file://webnovel-writer/dashboard/app.py#L139-L141)
- [webnovel-writer/dashboard/app.py:156-159](file://webnovel-writer/dashboard/app.py#L156-L159)
- [webnovel-writer/dashboard/path_guard.py:20-26](file://webnovel-writer/dashboard/path_guard.py#L20-L26)

## 结论
本规范覆盖了 Webnovel Writer 工作台的核心 API，强调只读查询、安全文件访问、异步任务与实时事件推送。新增的题材与金手指管理、项目管理、大纲树与活动追踪功能进一步完善了工作台的项目生命周期管理能力。通过路径守卫与严格的参数校验，保障系统安全性与稳定性。建议在生产环境结合反向代理与鉴权网关增强安全防护。

## 附录

### 认证机制
- 无内置认证：所有端点默认开放
- 建议在网关层添加鉴权与速率限制

### 错误处理策略
- 明确的 HTTP 状态码与错误信息
- 对数据库与文件系统的异常进行捕获与转换
- SSE 订阅队列满时自动清理无效订阅
- **新增** 项目创建与切换的专用错误处理

### 数据验证规则
- 字符串参数必须为字符串类型
- 对象参数必须为 JSON 对象
- 路径参数必须通过安全解析与目录白名单校验
- **新增** 创建项目时 title 参数必须非空

### 版本兼容性
- 扩展表接口仅在 v5.3+ 或 v5.4+ 可用
- index.db 表结构变化时，查询逻辑具备容错（表不存在返回空）
- **新增** 题材与项目管理功能适用于所有版本

### 请求/响应示例与状态码
- 示例
  - GET /api/project/info：返回 state.json 内容
  - GET /api/workbench/summary：返回 pages、project、progress、workspaces 等
  - GET /api/entities?type=character&include_archived=false：返回实体列表
  - GET /api/files/read?path=正文/01.md：返回 { path, content }
  - POST /api/files/save：返回 { path, saved_at, size }
  - POST /api/tasks：返回任务快照
  - POST /api/chat：返回 { reply, suggested_actions, reason, scope }
  - GET /api/events：SSE 流，推送 file.changed 与 task.updated
  - **新增** GET /api/genres：返回题材列表
  - **新增** GET /api/golden-finger-types：返回金手指类型列表
  - **新增** POST /api/project/create：返回创建结果
  - **新增** GET /api/projects：返回项目列表
  - **新增** GET /api/outline/tree：返回大纲树结构
  - **新增** GET /api/recent-activity：返回最近活动
- 状态码
  - 200：成功
  - 400：参数错误或业务逻辑错误
  - 403：路径越界或权限不足
  - 404：资源不存在
  - 500：服务器内部错误

### 使用场景演示
- 初始化工作台：调用 /api/project/info 与 /api/workbench/summary
- 查看实体：调用 /api/entities 列表与 /api/entities/{id}
- 编辑文件：先读取 /api/files/read，再写入 /api/files/save
- 执行动作：POST /api/chat 获取建议动作，再 POST /api/tasks 创建任务
- 实时同步：GET /api/events 订阅文件与任务事件
- **新增** 项目管理：调用 /api/genres 与 /api/golden-finger-types 获取创建选项，POST /api/project/create 创建项目，GET /api/projects 获取项目列表，POST /api/project/switch 切换项目
- **新增** 大纲管理：GET /api/outline/tree 获取大纲树结构，用于卷级规划与导航

### API 集成指南
- 后端启动
  - 使用 dashboard/server.py 指定项目根目录、主机与端口
  - 默认监听 127.0.0.1:8765，自动打开浏览器并指向 /docs
- 前端接入
  - 使用 frontend/src/api.js 中的工具函数封装请求
  - 通过 EventSource 订阅 /api/events，处理 file.changed 与 task.updated
  - **新增** 使用新增的 API 函数：fetchGenres()、fetchGoldenFingerTypes()、createProject()、fetchProjects()、switchProject()、fetchOutlineTree()、fetchRecentActivity()
- 任务执行
  - 创建任务后轮询 /api/tasks/{id} 获取结果
  - 或订阅 SSE 获取实时状态
- **新增** 项目管理集成
  - 在创建向导中调用 /api/genres 与 /api/golden-finger-types 获取选项
  - 调用 /api/project/create 创建新项目
  - 调用 /api/projects 获取项目列表，支持项目切换

**章节来源**
- [webnovel-writer/dashboard/server.py:43-72](file://webnovel-writer/dashboard/server.py#L43-L72)
- [webnovel-writer/dashboard/frontend/src/api.js:1-78](file://webnovel-writer/dashboard/frontend/src/api.js#L1-L78)
- [webnovel-writer/dashboard/frontend/src/api.js:79-100](file://webnovel-writer/dashboard/frontend/src/api.js#L79-L100)

### 客户端实现模板
- JavaScript（Fetch + EventSource）
  - 参考路径：[webnovel-writer/dashboard/frontend/src/api.js:7-77](file://webnovel-writer/dashboard/frontend/src/api.js#L7-L77)
  - **新增** 新增 API 函数模板：fetchGenres()、fetchGoldenFingerTypes()、createProject()、fetchProjects()、switchProject()、fetchOutlineTree()、fetchRecentActivity()
- Python（requests + sseclient）
  - 参考路径：[webnovel-writer/scripts/data_modules/api_client.py:1-496](file://webnovel-writer/scripts/data_modules/api_client.py#L1-L496)

### 测试用例
- 单元测试
  - 实体查询：覆盖表存在/不存在、过滤条件与排序
  - 文件安全：路径越界、非文本文件读取
  - 任务状态：创建、运行、完成、失败
  - SSE：事件推送与断线重连
  - **新增** 题材与金手指：GET /api/genres 与 GET /api/golden-finger-types 的契约测试
  - **新增** 项目管理：POST /api/project/create、GET /api/projects、POST /api/project/switch 的契约测试
  - **新增** 大纲树与活动：GET /api/outline/tree 与 GET /api/recent-activity 的契约测试
- 端到端测试
  - 工作台摘要：聚合项目信息与进度
  - 聊天意图：关键词匹配与动作建议
  - 文件树：三大目录遍历与大小统计
  - **新增** 项目生命周期：创建、切换、列表的完整流程测试

**章节来源**
- [webnovel-writer/dashboard/app.py:114-347](file://webnovel-writer/dashboard/app.py#L114-L347)
- [webnovel-writer/dashboard/path_guard.py:11-28](file://webnovel-writer/dashboard/path_guard.py#L11-L28)
- [webnovel-writer/dashboard/task_service.py:66-120](file://webnovel-writer/dashboard/task_service.py#L66-L120)
- [webnovel-writer/dashboard/workbench_service.py:18-55](file://webnovel-writer/dashboard/workbench_service.py#L18-L55)
- [webnovel-writer/dashboard/watcher.py:63-77](file://webnovel-writer/dashboard/watcher.py#L63-L77)
- [webnovel-writer/dashboard/frontend/src/api.js:61-77](file://webnovel-writer/dashboard/frontend/src/api.js#L61-L77)
- [webnovel-writer/dashboard/tests/test_new_apis.py:1-318](file://webnovel-writer/dashboard/tests/test_new_apis.py#L1-L318)