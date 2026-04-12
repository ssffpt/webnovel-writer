# Web Workbench Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前只读 Dashboard 演进为可编辑的三页面 Web 工作台骨架，先跑通“大纲 / 章节 / 设定”的浏览与保存闭环，并预留聊天、动作卡、任务面板的接入位。

**Architecture:** 保留现有 FastAPI + React/Vite 底座，先进行前端壳层重组和后端读写 API 扩展，不在 Phase 1 直接深度改造 Claude Code 执行链。前端先完成三栏工作台、页面切换、编辑器与右侧统一侧栏；后端先完成文件读取归一化、保存接口和最小的任务/聊天占位响应。

**Tech Stack:** FastAPI, React 19, Vite 6, 原生 fetch/EventSource, Python pathlib/json/sqlite, 现有 dashboard 静态托管机制

## Existing Dashboard Evolution Contract

本计划默认 **在现有 dashboard 基础上演进**，不是新建独立前后端项目。执行时必须遵守以下约束：

- 修改主落点是 `webnovel-writer/dashboard/app.py`、`webnovel-writer/dashboard/server.py`、`webnovel-writer/dashboard/frontend/`
- 复用现有 FastAPI 路由、静态托管和前端工程，不新建平行的 Web 应用
- 复用现有 Claude Code 写作链路、Skills、Agents 与 `.webnovel` 数据层，不在 Phase 1 重写底层写作流程
- Phase 1 的目标是把只读 dashboard 升级为可编辑 workbench 骨架，而不是替换现有 dashboard

---

## File Structure

### Backend
- Modify: `webnovel-writer/dashboard/app.py` — 从当前单文件 API 扩展为支持项目摘要、文件树/读取归一化、文件保存、占位任务接口、占位聊天接口
- Create: `webnovel-writer/dashboard/models.py` — 定义最小响应结构与辅助函数（可选轻量，不引入复杂依赖）
- Create: `webnovel-writer/dashboard/workbench_service.py` — 聚合项目摘要、文件映射、保存逻辑，减少 `app.py` 膨胀

### Frontend
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx` — 从当前单页面仪表盘切换为三页面工作台壳层
- Modify: `webnovel-writer/dashboard/frontend/src/api.js` — 增加 save/task/chat 接口封装
- Modify: `webnovel-writer/dashboard/frontend/src/index.css` — 增加工作台三栏布局、编辑区、侧栏与状态样式
- Create: `webnovel-writer/dashboard/frontend/src/workbench/data.js` — 页面 schema、占位动作、默认标签与前端映射
- Create: `webnovel-writer/dashboard/frontend/src/workbench/hooks.js` — 封装页面数据加载、保存、SSE 刷新、dirty 状态逻辑
- Create: `webnovel-writer/dashboard/frontend/src/workbench/TopBar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`

### Verification / Docs
- Test manually: `python3.11 -m dashboard.server --project-root <project_root> --no-browser`
- Test manually: `cd webnovel-writer/dashboard/frontend && npm run build`

---

## Task 1: 梳理后端工作台数据模型与路由骨架

**Files:**
- Create: `webnovel-writer/dashboard/workbench_service.py`
- Create: `webnovel-writer/dashboard/models.py`
- Modify: `webnovel-writer/dashboard/app.py`
- Test: manual API checks via `curl`

- [ ] **Step 1: 写出目标数据契约注释与辅助结构**

在 `models.py` 中定义 Phase 1 用到的最小数据结构（可用 TypedDict / dataclass / 纯注释常量），至少覆盖：

```python
WORKBENCH_PAGES = ("chapters", "outline", "settings")

TASK_STATUSES = (
    "idle",
    "pending",
    "running",
    "completed",
    "failed",
)
```

以及接口约定：
- `/api/workbench/summary`
- `/api/files/save`
- `/api/tasks/current`
- `/api/chat`

- [ ] **Step 2: 在 `workbench_service.py` 封装项目摘要读取**

实现以下函数骨架：

```python
from pathlib import Path
from typing import Any


def load_project_summary(project_root: Path) -> dict[str, Any]:
    ...


def load_workspace_tree(project_root: Path) -> dict[str, Any]:
    ...


def save_workspace_file(project_root: Path, relative_path: str, content: str) -> dict[str, Any]:
    ...
```

要求：
- 只允许读写 `正文/`、`大纲/`、`设定集/`
- 保存前用现有 `safe_resolve()` 校验
- 返回 `path`、`saved_at`、`size` 等最小元数据

- [ ] **Step 3: 在 `app.py` 中加入 Phase 1 新接口**

新增以下路由：

```python
@app.get("/api/workbench/summary")
def workbench_summary(): ...

@app.post("/api/files/save")
def save_file(payload: dict): ...

@app.get("/api/tasks/current")
def current_task(): ...

@app.post("/api/chat")
def chat(payload: dict): ...
```

Phase 1 约束：
- `current_task` 先返回占位空闲状态
- `chat` 先做规则版动作建议，不接模型
- 不删除旧接口，确保旧 Dashboard 数据接口仍可访问

- [ ] **Step 4: 为 `chat` 返回固定结构**

返回格式固定为：

```json
{
  "reply": "...",
  "suggested_actions": [
    {
      "type": "write_chapter",
      "label": "生成当前章节",
      "params": {"chapter": 18}
    }
  ]
}
```

规则优先识别：
- “写/生成章节” → `write_chapter`
- “审查/检查章节” → `review_chapter`
- “规划/卷纲/章纲” → `plan_outline`
- “设定/人物/世界观” → `inspect_setting`

- [ ] **Step 5: 手动验证接口形状**

运行：

```bash
PYTHONPATH=/Users/liushuang/Projects/webnovel-writer/webnovel-writer python3.11 -m dashboard.server --project-root /tmp/webnovel-demo-project --no-browser
```

验证：

```bash
curl -s http://127.0.0.1:8765/api/workbench/summary
curl -s http://127.0.0.1:8765/api/tasks/current
curl -s -X POST http://127.0.0.1:8765/api/chat -H 'Content-Type: application/json' -d '{"message":"帮我规划第二卷"}'
```

Expected:
- summary 返回三工作区所需最小摘要
- current_task 返回 idle 占位结构
- chat 返回 reply + suggested_actions

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/app.py webnovel-writer/dashboard/models.py webnovel-writer/dashboard/workbench_service.py
git commit -m "Establish the Phase 1 workbench API skeleton"
```

---

## Task 2: 重构前端为三页面工作台壳层

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/TopBar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/data.js`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: `npm run build`

- [ ] **Step 1: 定义三页面常量与顶栏导航**

在 `workbench/data.js` 中写出：

```js
export const WORKBENCH_PAGES = [
  { id: 'chapters', label: '章节' },
  { id: 'outline', label: '大纲' },
  { id: 'settings', label: '设定' },
]
```

- [ ] **Step 2: 将 `App.jsx` 改为工作台壳层**

新的顶层状态至少包括：

```js
const [page, setPage] = useState('chapters')
const [summary, setSummary] = useState(null)
const [currentTask, setCurrentTask] = useState({ status: 'idle' })
const [chatMessages, setChatMessages] = useState([])
const [suggestedActions, setSuggestedActions] = useState([])
```

页面渲染切换为：
- `ChapterPage`
- `OutlinePage`
- `SettingPage`

- [ ] **Step 3: 新建 `TopBar.jsx` 与 `RightSidebar.jsx`**

`TopBar.jsx` 显示：
- 项目名
- 页面切换按钮
- 当前任务状态小徽标

`RightSidebar.jsx` 组合三块：
- ContextPanel（当前对象提示）
- ChatPanel（消息 + 输入框）
- TaskPanel（当前任务）

Phase 1 可以先把三块都写在一个文件里，后续再拆。

- [ ] **Step 4: 为工作台增加三栏布局 CSS**

至少增加这些类：

```css
.workbench-shell {}
.workbench-topbar {}
.workbench-body {}
.workbench-left {}
.workbench-center {}
.workbench-right {}
.editor-shell {}
.action-list {}
.task-card {}
```

要求：
- 左栏固定宽度
- 中栏自适应
- 右栏固定宽度
- 保留移动端退化的基本可读性

- [ ] **Step 5: 构建前端确认无语法错误**

运行：

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard/frontend
npm run build
```

Expected: `vite build` 成功输出 dist

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Replace the dashboard shell with a three-page workbench shell"
```

---

## Task 3: 接入章节工作台的读取、编辑与保存闭环

**Files:**
- Create: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/api.js`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: manual save flow

- [ ] **Step 1: 在 `api.js` 增加保存与聊天方法**

新增：

```js
export async function postJSON(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}
```

以及：
- `saveFile(path, content)`
- `sendChat(message, context)`

- [ ] **Step 2: 在 `ChapterPage.jsx` 实现左栏章节列表与中栏编辑器**

状态至少包含：

```js
const [selectedPath, setSelectedPath] = useState(null)
const [draft, setDraft] = useState('')
const [dirty, setDirty] = useState(false)
const [saveState, setSaveState] = useState('idle')
```

交互：
- 左侧点章节后加载内容
- 编辑正文时标记 dirty
- 点击保存调用 `/api/files/save`

- [ ] **Step 3: 在章节页加入最小动作按钮**

按钮：
- 保存
- 按大纲生成
- 审查本章

Phase 1 中“按大纲生成 / 审查本章”先不真正跑任务，可将动作写入右侧 `suggestedActions` 或触发占位提示。

- [ ] **Step 4: 连接右侧上下文与聊天**

章节页切换选中项时，右侧上下文至少显示：
- 当前章节路径
- 是否有未保存改动
- 是否可执行写作动作

聊天发送时追加上下文：

```js
{
  page: 'chapters',
  selectedPath,
}
```

- [ ] **Step 5: 手动验证保存闭环**

验证顺序：
1. 打开某个章节
2. 修改正文
3. 点击保存
4. 刷新页面
5. 确认内容保留

Expected:
- 保存成功提示可见
- dirty 状态清空
- 文件内容真实落盘

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/api.js webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Implement the chapter workspace edit-and-save loop"
```

---

## Task 4: 接入大纲工作台的树导航与保存闭环

**Files:**
- Create: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: manual outline save flow

- [ ] **Step 1: 用现有 `/api/files/tree` 的 `大纲` 节点驱动左栏**

左栏显示：
- 总纲
- 卷纲
- 章纲

如无数据，显示空状态提示“先创建总纲或章纲”。

- [ ] **Step 2: 在中栏复用与章节页相同的文本编辑模式**

状态模式保持一致：
- `selectedPath`
- `draft`
- `dirty`
- `saveState`

减少心智切换。

- [ ] **Step 3: 实现三个主按钮**

按钮：
- 保存
- 生成卷纲
- 生成章纲

Phase 1 中后两者先走占位动作卡：

```js
setSuggestedActions([
  { type: 'plan_outline', label: '生成当前卷纲', params: { path: selectedPath } }
])
```

- [ ] **Step 4: 加入辅助信息区**

显示：
- 当前节点类型
- 是否已有对应正文
- 是否建议开始写作

这些信息可以先由前端根据路径与 `summary` 粗略推断。

- [ ] **Step 5: 手动验证大纲保存闭环**

Expected:
- 点击不同大纲节点可切换内容
- 编辑保存成功
- 重新加载后内容存在

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Implement the outline workspace navigation and save loop"
```

---

## Task 5: 接入设定工作台的分类浏览与保存闭环

**Files:**
- Create: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: manual settings save flow

- [ ] **Step 1: 约定设定数据来源映射**

优先读取 `设定集/` 目录；左栏先按固定分类切分：
- 人物
- 势力
- 地点
- 世界观

若目录内实际文件不匹配，仍允许全部回退到“全部条目”显示。

- [ ] **Step 2: 实现设定页双层左栏**

左栏上部为分类标签，下部为当前分类条目列表。

示例状态：

```js
const [category, setCategory] = useState('人物')
const [selectedPath, setSelectedPath] = useState(null)
```

- [ ] **Step 3: 实现设定编辑器与保存**

中栏至少提供：
- 名称显示
- 内容编辑区
- 保存按钮
- 保存状态

- [ ] **Step 4: 实现“检查冲突”占位动作**

先不接真实执行链，只把动作卡放到右栏：

```js
{ type: 'inspect_setting', label: '检查当前设定冲突', params: { path: selectedPath } }
```

- [ ] **Step 5: 手动验证设定保存闭环**

Expected:
- 分类切换不报错
- 条目加载正常
- 文本可编辑并保存

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Implement the settings workspace browse-and-save loop"
```

---

## Task 6: 做右侧聊天、动作卡、任务卡的统一占位体验

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/api.js`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: manual chat and action flow

- [ ] **Step 1: 定义右侧栏输入输出协议**

Props 至少包含：

```js
{
  context,
  chatMessages,
  onSendMessage,
  suggestedActions,
  onRunAction,
  currentTask,
}
```

- [ ] **Step 2: 聊天发送后调用 `/api/chat`**

流程：
1. 本地先追加用户消息
2. 调 `sendChat(message, context)`
3. 返回后追加 AI 回复
4. 用返回的 `suggested_actions` 刷新动作卡

- [ ] **Step 3: 实现统一动作卡展示**

每张卡展示：
- 标题
- 说明
- 作用对象
- 执行按钮
- 取消按钮

Phase 1 的 `onRunAction` 行为：
- 把 `currentTask` 设为 `pending`
- 1 秒后模拟回到 `idle` 或 `completed`
- 明确标识“占位流程，真实执行待 Phase 2 接入”

- [ ] **Step 4: 实现当前任务卡**

显示：
- 状态
- 当前动作名
- 当前步骤文本
- 最近更新时间

- [ ] **Step 5: 手动验证端到端体验**

验证：
- 在三个页面都能看到统一右栏
- 输入聊天能返回 AI 回复和动作卡
- 点击动作卡会刷新任务卡

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx webnovel-writer/dashboard/frontend/src/api.js webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Add the shared chat, action, and task sidebar for the MVP workbench"
```

---

## Task 7: 全量验证并补齐 Phase 2 接入前的边界说明

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-web-workbench-design.md`
- Test: backend + frontend build + manual runbook

- [ ] **Step 1: 运行前端构建**

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard/frontend
npm run build
```

Expected: build 成功

- [ ] **Step 2: 运行后端服务并人工走查三页面**

```bash
PYTHONPATH=/Users/liushuang/Projects/webnovel-writer/webnovel-writer python3.11 -m dashboard.server --project-root /tmp/webnovel-demo-project --no-browser
```

人工验证：
- 章节页可读写
- 大纲页可读写
- 设定页可读写
- 右栏聊天可返回动作卡
- 任务卡状态能变化

- [ ] **Step 3: 在 spec 中记录 Phase 1 完成定义**

补一节 “Phase 1 Done Means” ：
- 三页面布局稳定
- 三类内容可读写
- 聊天/动作/任务 UI 可用
- 真实 Claude 执行链尚未接入，仅有占位流

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/specs/2026-04-12-web-workbench-design.md
git commit -m "Document the Phase 1 completion bar for the MVP workbench"
```

---

## Self-Review

### Spec coverage
- 三页面 MVP：Task 2-5 覆盖
- 全局右栏：Task 6 覆盖
- 文件读取/保存闭环：Task 1, 3, 4, 5 覆盖
- 聊天动作卡占位：Task 1, 6 覆盖
- 当前任务占位：Task 1, 6 覆盖
- Phase 2 真实动作接入前边界：Task 7 覆盖

### Placeholder scan
- 未使用 TBD/TODO
- 每个任务均列出精确文件与验证方式
- Phase 1 中未接入的能力明确标为“占位”，非模糊描述

### Type consistency
- 页面 ID 统一为 `chapters` / `outline` / `settings`
- 任务状态统一为 `idle` / `pending` / `running` / `completed` / `failed`
- 动作类型统一为 `write_chapter` / `review_chapter` / `plan_outline` / `inspect_setting`
