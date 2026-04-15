# Web Workbench Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前只读 Dashboard 演进为可编辑的四页面 Web 工作台骨架，先落地“总览 / 大纲 / 章节 / 设定”的页面结构，跑通大纲 / 章节 / 设定的浏览与保存闭环，并预留聊天、动作卡、任务面板的接入位。

**Architecture:** 保留现有 FastAPI + React/Vite 底座，先进行前端壳层重组和后端读写 API 扩展，不在 Phase 1 直接深度改造 Claude Code 执行链。前端先完成三栏工作台、四页面切换、总览页、三个编辑工作区与右侧统一侧栏；后端先完成总览聚合、文件读取归一化、保存接口和最小的任务/聊天占位响应。

**Tech Stack:** FastAPI, React 19, Vite 6, 原生 fetch/EventSource, Python pathlib/json/sqlite, 现有 dashboard 静态托管机制

## Existing Dashboard Evolution Contract

本计划默认 **在现有 dashboard 基础上演进**，不是新建独立前后端项目。执行时必须遵守以下约束：

- 修改主落点是 `webnovel-writer/dashboard/app.py`、`webnovel-writer/dashboard/server.py`、`webnovel-writer/dashboard/frontend/`
- 复用现有 FastAPI 路由、静态托管和前端工程，不新建平行的 Web 应用
- 复用现有 Claude Code 写作链路、Skills、Agents 与 `.webnovel` 数据层，不在 Phase 1 重写底层写作流程
- Phase 1 的目标是把只读 dashboard 升级为可编辑 workbench 骨架，而不是替换现有 dashboard

## Real-Codebase Execution Notes

基于当前仓库真实结构，执行时额外遵守以下约束，避免“计划写得出但实际落不下”：

- 当前后端所有路由都集中在 `webnovel-writer/dashboard/app.py`，且 CORS 目前只允许 `GET`；在增加 `POST /api/files/save` 与 `POST /api/chat` 前，必须先把 `allow_methods=["GET"]` 调整为至少允许 `POST`，否则前端浏览器请求会直接失败。
- `app.py` 顶部模块说明当前仍写着“仅提供 GET 接口（严格只读）”；在引入保存接口时必须同步更新模块注释，避免代码语义和文档注释互相冲突。
- 现有 `/api/files/tree` 与 `/api/files/read` 已经存在，且内部已复用 `_walk_tree()`、`_is_child()` 与 `safe_resolve()`；Phase 1 应在这些现有能力上扩展，不要在 `workbench_service.py` 里重复造一套树遍历与路径校验逻辑。
- 现有 SSE `/api/events` 只监听 `.webnovel/` 目录变化，不监听 `正文/`、`大纲/`、`设定集/` 文件保存；因此 Phase 1 的编辑保存体验不能把“保存后依赖 SSE 自动刷新”当作前提，保存成功后应以内存状态更新或主动重新拉取为主。
- 当前前端只有 `App.jsx / api.js / index.css / main.jsx` 四个源码文件，且 `App.jsx` 是一个巨型旧 dashboard 入口；Phase 1 应接受“先替换 `App.jsx` 主壳层、把新工作台拆到 `src/workbench/`”的演进方式，不要假设已经存在可复用的页面级组件目录。
- 当前前端依赖包含 `react-force-graph-3d`，它服务于旧“关系图谱”页面；Phase 1 新工作台不再以该页面为顶级入口，但本阶段不需要移除该依赖，也不应把“清理旧依赖”混入工作台骨架任务。
- `dashboard/server.py` 已经提供稳定启动入口，计划中的人工验证应继续使用 `python3.11 -m dashboard.server ...`，不要再设计新的本地启动脚本。

## Recommended Execution Order and Risk Ranking

为了避免执行时“先做了表层 UI，最后被底层接口或跨页状态卡死”，建议按下面的风险排序推进：

### P0：最先完成，属于阻塞型前置条件

1. **后端允许 POST + 修正只读语义**
   - 涉及：`app.py` 的 CORS `allow_methods`、模块注释、`/api/files/save`、`/api/chat`、`/api/tasks/current`
   - 原因：如果仍停留在 GET-only，后续前端聊天/保存联调会全部假失败
   - 风险：高
   - 阻塞范围：Task 2-7

2. **`/api/workbench/summary` 与最小数据契约落地**
   - 涉及：`models.py`、`workbench_service.py`、`app.py`
   - 原因：总览页、顶栏项目名、右栏上下文、页面空状态都依赖这个聚合摘要
   - 风险：高
   - 阻塞范围：Task 2, 6, 7

3. **文件读写边界统一**
   - 涉及：只允许 `正文/`、`大纲/`、`设定集/`；复用 `safe_resolve()`；保存返回一致元数据
   - 原因：三个编辑工作区都建立在这条边界上，若这里不稳，后面每页都会各自打补丁
   - 风险：高
   - 阻塞范围：Task 3, 4, 5, 7

### P1：第二批完成，属于主干骨架

4. **替换 `App.jsx` 为四页面 workbench 壳层**
   - 涉及：`App.jsx`、`workbench/data.js`、`TopBar.jsx`、`RightSidebar.jsx`
   - 原因：这是从旧 dashboard 迁移到新信息架构的主骨架，越早稳定越能减少返工
   - 风险：高
   - 阻塞范围：Task 3, 4, 5, 6

5. **先落总览页，再接三个编辑页**
   - 涉及：`OverviewPage.jsx`
   - 原因：总览页依赖最少，是验证四页面路由、摘要聚合、空状态处理是否合理的最低风险切入口
   - 风险：中
   - 阻塞范围：非强阻塞，但能提前暴露 summary 设计问题

6. **统一右侧栏 props 协议**
   - 涉及：`RightSidebar.jsx`、`App.jsx`
   - 原因：如果每个页面各自定义右栏输入输出，后面会非常难收口
   - 风险：中高
   - 阻塞范围：Task 3, 4, 5, 6

### P2：第三批完成，属于页面闭环

7. **章节页优先**
   - 原因：章节页是最高频入口，且“列表 → 打开 → 编辑 → 保存”链路最直观，最适合作为第一个编辑闭环
   - 风险：中
   - 建议顺序：先章节，再大纲，再设定

8. **大纲页第二**
   - 原因：大纲页会暴露目录层级不规范、章纲/卷纲命名不统一等结构问题，应在章节页稳定后处理
   - 风险：中高

9. **设定页第三**
   - 原因：设定目录往往最不规整，分类映射和“全部条目”退化逻辑需要更多兜底
   - 风险：中高

### P3：最后完成，属于占位体验和总验收

10. **聊天 / 动作卡 / 任务卡占位**
    - 原因：这些在 Phase 1 不接真实执行链，不应抢在主编辑闭环之前做重
    - 风险：中
    - 说明：先打通静态结构和规则回复即可

11. **最终联调与验收**
    - 原因：必须在四页面壳层、三个编辑闭环、右栏协议都稳定后再做，否则只会重复验收
    - 风险：中

### 不建议的错误顺序

- **先做右栏聊天，再补后端 POST**
  - 结果：前端看似完成，实际一联调就被 CORS/方法限制卡死

- **先做三个编辑页，再补 summary**
  - 结果：总览页、顶栏、右栏上下文会各写各的临时状态，后面难统一

- **先追求 SSE 自动刷新，再做保存闭环**
  - 结果：会被当前 watcher 仅监听 `.webnovel/` 的事实拖住，偏离 Phase 1 目标

- **把旧 dashboard 的图谱/分析页一起迁移**
  - 结果：范围膨胀，四页面工作台骨架迟迟无法稳定

### 推荐实际执行串行顺序

建议按以下顺序落地：

1. Task 1（后端骨架与契约）
2. Task 2（四页面壳层 + 总览页）
3. Task 3（章节页闭环）
4. Task 4（大纲页闭环）
5. Task 5（设定页闭环）
6. Task 6（右栏占位体验）
7. Task 7（全量验证）

如需并行，最多建议：
- 一人处理 **Task 1**
- 一人准备 **Task 2 的纯前端壳层/CSS**

但 **Task 3-6 不建议在 Task 2 未稳定前并行展开**，否则接口、props、状态模型会来回返工。

---

## File Structure

### Backend
- Modify: `webnovel-writer/dashboard/app.py` — 从当前单文件 API 扩展为支持工作台摘要、文件树/读取归一化、文件保存、占位任务接口、占位聊天接口
- Create: `webnovel-writer/dashboard/models.py` — 定义最小响应结构与辅助函数（可选轻量，不引入复杂依赖）
- Create: `webnovel-writer/dashboard/workbench_service.py` — 聚合总览页摘要、文件映射、保存逻辑，减少 `app.py` 膨胀

### Frontend
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx` — 从当前单页面仪表盘切换为四页面工作台壳层
- Modify: `webnovel-writer/dashboard/frontend/src/api.js` — 增加 save/task/chat 接口封装
- Modify: `webnovel-writer/dashboard/frontend/src/index.css` — 增加工作台三栏布局、编辑区、侧栏与状态样式
- Create: `webnovel-writer/dashboard/frontend/src/workbench/data.js` — 页面 schema、占位动作、默认标签与前端映射
- Create: `webnovel-writer/dashboard/frontend/src/workbench/hooks.js` — 封装页面数据加载、保存、SSE 刷新、dirty 状态逻辑
- Create: `webnovel-writer/dashboard/frontend/src/workbench/TopBar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`
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
WORKBENCH_PAGES = ("overview", "chapters", "outline", "settings")

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
- 尽量复用 `app.py` 中现有的 `_walk_tree()` / `_is_child()` 语义，避免产生两套树结构格式
- `load_project_summary()` 对缺失的目录或缺失的可选数据要返回空结构而不是抛异常，保证总览页可降级显示

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
- 在新增 `POST` 路由前先放开 FastAPI CORS `allow_methods`
- 更新 `app.py` 顶部“只读/GET-only”说明，避免与实际行为冲突

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
- summary 返回总览页 + 三工作区所需最小摘要
- current_task 返回 idle 占位结构
- chat 返回 reply + suggested_actions
- 浏览器控制台中对 `POST /api/chat` 与后续 `POST /api/files/save` 不应出现 CORS method blocked

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/app.py webnovel-writer/dashboard/models.py webnovel-writer/dashboard/workbench_service.py
git commit -m "Establish the Phase 1 workbench API skeleton"
```

---

## Task 2: 重构前端为四页面工作台壳层

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/TopBar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`
- Create: `webnovel-writer/dashboard/frontend/src/workbench/data.js`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: `npm run build`

- [ ] **Step 1: 定义四页面常量与顶栏导航**

在 `workbench/data.js` 中写出：

```js
export const WORKBENCH_PAGES = [
  { id: 'overview', label: '总览' },
  { id: 'chapters', label: '章节' },
  { id: 'outline', label: '大纲' },
  { id: 'settings', label: '设定' },
]
```

- [ ] **Step 2: 将 `App.jsx` 改为工作台壳层**

新的顶层状态至少包括：

```js
const [page, setPage] = useState('overview')
const [summary, setSummary] = useState(null)
const [currentTask, setCurrentTask] = useState({ status: 'idle' })
const [chatMessages, setChatMessages] = useState([])
const [suggestedActions, setSuggestedActions] = useState([])
```

页面渲染切换为：
- `OverviewPage`
- `ChapterPage`
- `OutlinePage`
- `SettingPage`

- [ ] **Step 3: 新建 `OverviewPage.jsx` 承接轻量总览页**

`OverviewPage.jsx` 负责显示：
- 项目概况
- 最近任务
- 最近修改
- AI 下一步建议
- 跳转卡片（去章节 / 去大纲 / 去设定 / 查看当前任务）

约束：
- 不承载复杂统计图表
- 不重建旧 dashboard 的分析页集合
- 可优先使用 `summary` 中的聚合字段渲染
- 即使 `summary` 只返回最小聚合字段，也必须能稳定渲染空状态，不依赖旧 `DashboardPage` 的完整统计数据

- [ ] **Step 4: 新建 `TopBar.jsx` 与 `RightSidebar.jsx`**

`TopBar.jsx` 显示：
- 项目名
- 页面切换按钮
- 当前任务状态小徽标

`RightSidebar.jsx` 组合三块：
- ContextPanel（当前对象提示）
- ChatPanel（消息 + 输入框）
- TaskPanel（当前任务）

Phase 1 可以先把三块都写在一个文件里，后续再拆。

- [ ] **Step 5: 为工作台增加三栏布局 CSS**

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
- 不要求与旧 dashboard CSS 共存两套完整信息架构；允许以 workbench 样式为主覆盖旧主壳层

- [ ] **Step 6: 构建前端确认无语法错误**

运行：

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard/frontend
npm run build
```

Expected: `vite build` 成功输出 dist

- [ ] **Step 7: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Replace the dashboard shell with a four-page workbench shell"
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
- 即使没有 SSE 推送，保存后当前页状态也能立即反映最新内容

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

注意：
- 若当前项目缺少标准化“总纲 / 卷纲 / 章纲”层级，也必须能退化为普通文件列表，不把大纲页实现绑定到理想目录结构

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
- 当设定目录命名不规范时，仍可通过“全部条目”退化路径完成浏览与保存

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
- 不要求接入 SSE 驱动的任务流；允许由前端本地状态模拟

- [ ] **Step 4: 实现当前任务卡**

显示：
- 状态
- 当前动作名
- 当前步骤文本
- 最近更新时间

- [ ] **Step 5: 手动验证端到端体验**

验证：
- 在四个页面都能看到统一右栏
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

- [ ] **Step 2: 运行后端服务并人工走查四页面**

```bash
PYTHONPATH=/Users/liushuang/Projects/webnovel-writer/webnovel-writer python3.11 -m dashboard.server --project-root /tmp/webnovel-demo-project --no-browser
```

人工验证：
- 总览页可正常展示项目摘要 / 最近任务 / AI 建议
- 章节页可读写
- 大纲页可读写
- 设定页可读写
- 右栏聊天可返回动作卡
- 任务卡状态能变化
- 浏览器中保存/聊天请求没有被 CORS 拦截
- 在没有 `.webnovel` 外部文件变更 SSE 的前提下，三个编辑工作区仍能稳定使用

- [ ] **Step 3: 在 spec 中记录 Phase 1 完成定义**

补一节 “Phase 1 Done Means” ：
- 四页面布局稳定
- 总览页为轻量入口页，不承载复杂分析
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
- 四页面 MVP：Task 2-5, 7 覆盖
- 全局右栏：Task 6 覆盖
- 文件读取/保存闭环：Task 1, 3, 4, 5 覆盖
- 聊天动作卡占位：Task 1, 6 覆盖
- 当前任务占位：Task 1, 6 覆盖
- Phase 2 真实动作接入前边界：Task 7 覆盖

### Placeholder scan
- 未使用 TBD/TODO
- 每个任务均列出精确文件与验证方式
- Phase 1 中未接入的能力明确标为“占位”，非模糊描述

### Real-codebase fit check
- 已反映当前 `app.py` 为单文件后端入口的现实
- 已补充 CORS 从 GET-only 升级到允许 POST 的要求
- 已补充 SSE 仅监听 `.webnovel/`、不能作为编辑保存刷新前提的限制
- 已补充当前前端仍是单文件主壳层、需从 `App.jsx` 迁移到 `workbench/` 的现实

### Type consistency
- 页面 ID 统一为 `chapters` / `outline` / `settings`
- 任务状态统一为 `idle` / `pending` / `running` / `completed` / `failed`
- 动作类型统一为 `write_chapter` / `review_chapter` / `plan_outline` / `inspect_setting`
