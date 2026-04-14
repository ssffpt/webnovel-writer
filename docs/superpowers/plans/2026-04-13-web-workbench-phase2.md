# Web Workbench Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Phase 1 的占位动作卡与任务卡升级为真实任务执行链，支持从前端创建任务、查看任务状态与日志，并在任务完成后刷新相关工作区。

**Architecture:** 继续保留现有 FastAPI + React/Vite 底座，在 `dashboard` 内增加轻量任务状态层与 Claude 命令执行适配层。前端不引入复杂状态库，继续由 `App.jsx + workbench/*` 承接任务与聊天联动；后端先用进程内任务注册表完成单机单用户任务流，再为 Phase 3 预留聊天编排与动作升级接口。

**Tech Stack:** FastAPI, React 19, Vite 6, Python subprocess/threading/queue/pathlib/json, 原生 fetch/EventSource, 现有 dashboard 静态托管与 watcher 机制

## Existing Dashboard Evolution Contract

本计划默认 **在现有 dashboard 基础上演进**，不是新建独立前后端项目。执行时必须遵守以下约束：

- 修改主落点仍是 `webnovel-writer/dashboard/app.py`、`webnovel-writer/dashboard/frontend/src/` 与 `webnovel-writer/dashboard/` 下新增的小型服务文件
- 不新建平行 Web 服务；继续使用 `python3.11 -m dashboard.server` 作为唯一启动入口
- 复用现有 `POST /api/chat` 与 `GET /api/tasks/current`，在其基础上扩成真实任务链，而不是推翻重做另一套接口
- 保持 Phase 1 的四页面工作台结构不变，Phase 2 的重点是让右侧动作卡与任务卡真正工作

## Real-Codebase Execution Notes

基于当前仓库真实状态，Phase 2 执行时必须注意：

- 目前后端所有路由仍集中在 `webnovel-writer/dashboard/app.py`，Phase 2 可以新增 `task_service.py` / `claude_runner.py`，但不要一次性拆成过度细碎的包结构。
- 目前 `GET /api/tasks/current` 返回的是最小空闲占位结构，前端 `App.jsx` 已经直接读取它；Phase 2 扩展时必须保证空闲态结构向后兼容。
- 目前前端动作卡点击后仅使用 `setTimeout()` 模拟完成；Phase 2 改造时应先替换成真实 `POST /api/tasks`，而不是先把 UI 再复杂化。
- 当前 SSE `/api/events` 只监听 `.webnovel/` 目录变化，不会自动推送任务状态；Phase 2 如果需要任务实时状态，有两条路：
  1. 扩展现有 SSE，使其同时承载任务事件
  2. 增加轮询 `GET /api/tasks/{id}`
  本计划优先推荐 **扩展现有 SSE**，避免前端再加一套轮询器。
- 当前前端的 `RightSidebar.jsx` 已经具备聊天输入、动作卡和任务卡结构，Phase 2 应优先复用它，而不是再引入新的右栏组件体系。
- 当前 `workbench_service.py` 已承接 Phase 1 的 summary/save/chat helper；Phase 2 不要把任务执行逻辑再硬塞进去，应新建独立 `task_service.py` 承接任务生命周期。

## Recommended Execution Order and Risk Ranking

### P0：阻塞型前置项

1. **定义任务数据契约与状态机**
   - 涉及：任务 ID、动作类型、状态、日志项、结果结构
   - 风险：高
   - 原因：如果契约先天不稳，前后端都会反复改名和改字段

2. **后端最小任务注册表落地**
   - 涉及：进程内任务字典、线程安全、当前任务选择规则
   - 风险：高
   - 原因：没有真实任务状态层，就无法替换前端的占位模拟

3. **Claude 命令执行适配层落地**
   - 涉及：命令映射、stdout/stderr 捕获、退出码处理
   - 风险：高
   - 原因：Phase 2 的核心价值是“动作真跑”，不是任务卡 UI 再做一层样子

### P1：主干接线

4. **新增任务 API**
   - `POST /api/tasks`
   - `GET /api/tasks/{id}`
   - `POST /api/tasks/{id}/cancel`（可选但推荐先留壳）
   - 风险：高

5. **扩展现有 SSE 以推送任务状态与日志**
   - 风险：中高
   - 原因：比轮询更贴近现有工作台体验模型

6. **前端右栏改成真实任务交互**
   - 动作卡执行 -> 创建任务
   - 任务卡显示真实状态 / 步骤 / 更新时间 / 日志摘要
   - 风险：高

### P2：联动与刷新

7. **任务完成后刷新相关页面**
   - 章节动作完成后刷新章节内容
   - 大纲动作完成后刷新大纲列表/内容
   - 设定检查完成后刷新右栏结果与提示
   - 风险：中

8. **聊天与动作建议保持兼容**
   - `POST /api/chat` 仍可规则生成动作卡
   - 但动作卡执行要改为真实任务创建
   - 风险：中

### P3：收尾与验收

9. **失败路径与日志表现补齐**
   - 命令失败显示失败原因
   - 任务卡显示最新日志行与重试入口说明
   - 风险：中

10. **人工端到端验收**
   - 风险：中

## File Structure

### Backend
- Modify: `webnovel-writer/dashboard/app.py` — 新增任务 API、扩展 SSE 事件、接入任务服务
- Modify: `webnovel-writer/dashboard/models.py` — 增加任务状态常量、任务响应结构字段
- Create: `webnovel-writer/dashboard/task_service.py` — 进程内任务注册、状态流转、日志记录、事件广播
- Create: `webnovel-writer/dashboard/claude_runner.py` — 将 `write_chapter / review_chapter / plan_outline / inspect_setting` 映射到现有命令行执行
- Modify: `webnovel-writer/dashboard/workbench_service.py` — 如有必要，只补与任务完成后 summary 刷新有关的聚合字段
- Test: `webnovel-writer/dashboard/tests/test_phase2_tasks.py`

### Frontend
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx` — 用真实任务接口替换前端占位任务流，接任务事件刷新
- Modify: `webnovel-writer/dashboard/frontend/src/api.js` — 增加 `createTask` / `fetchTask` / `cancelTask` / 任务事件解析
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx` — 显示任务日志、失败原因、真实更新时间
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/data.js` — 统一任务状态与动作卡到任务卡的映射函数
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx` — 任务完成后刷新当前章节
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx` — 任务完成后刷新当前大纲
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx` — 任务完成后刷新设定页提示
- Modify: `webnovel-writer/dashboard/frontend/src/index.css` — 增加任务日志区域、失败态、运行态样式
- Test: `webnovel-writer/dashboard/frontend/tests/workbench.tasks.test.mjs`

### Verification / Docs
- Modify: `docs/superpowers/specs/2026-04-12-web-workbench-design.md` — 如实现过程中对任务状态、日志展示、刷新策略有明确收敛，补进 spec
- Create: `docs/superpowers/plans/2026-04-13-web-workbench-phase2.md`
- Test manually: `python3.11 -m dashboard.server --project-root <project_root> --no-browser`
- Test manually: `cd webnovel-writer/dashboard/frontend && npm run build`

---

## Task 1: 定义 Phase 2 任务契约与最小状态机

**Files:**
- Modify: `webnovel-writer/dashboard/models.py`
- Create: `webnovel-writer/dashboard/tests/test_phase2_tasks.py`

- [ ] **Step 1: 写第一条失败测试，锁定任务创建后的基础结构**

在 `test_phase2_tasks.py` 中先写：

```python
def test_create_task_returns_pending_task_with_id(...):
    ...
```

断言至少包含：
- `id`
- `status == "pending"`
- `action.type`
- `createdAt`
- `updatedAt`
- `logs == []`

- [ ] **Step 2: 运行该测试，确认先失败**

Run:

```bash
python3.11 -m pytest --no-cov webnovel-writer/dashboard/tests/test_phase2_tasks.py -q
```

Expected: FAIL，原因是 `/api/tasks` 尚未实现或返回结构不符合预期。

- [ ] **Step 3: 在 `models.py` 定义 Phase 2 任务状态常量**

至少补：

```python
TASK_STATUSES = (
    "idle",
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
)
```

并约定任务 payload 基本字段：
- `id`
- `status`
- `action`
- `createdAt`
- `updatedAt`
- `logs`
- `result`
- `error`

- [ ] **Step 4: Commit**

```bash
git add webnovel-writer/dashboard/models.py webnovel-writer/dashboard/tests/test_phase2_tasks.py
git commit -m "Define the Phase 2 task contract before wiring execution"
```

---

## Task 2: 落地进程内任务注册表与任务 API

**Files:**
- Create: `webnovel-writer/dashboard/task_service.py`
- Modify: `webnovel-writer/dashboard/app.py`
- Test: `webnovel-writer/dashboard/tests/test_phase2_tasks.py`

- [ ] **Step 1: 写失败测试，锁定任务创建与查询 API**

新增测试：

```python
def test_post_tasks_creates_task_and_get_task_returns_same_task(...):
    ...
```

断言：
- `POST /api/tasks` 返回 `202` 或 `200`
- `GET /api/tasks/{id}` 返回同一个任务 ID
- 初始状态为 `pending` 或 `running`

- [ ] **Step 2: 运行测试，确认失败**

Run 同上。

- [ ] **Step 3: 在 `task_service.py` 实现最小任务注册表**

至少实现：

```python
class TaskService:
    def create_task(self, action: dict, context: dict | None = None) -> dict: ...
    def get_task(self, task_id: str) -> dict: ...
    def get_current_task(self) -> dict: ...
    def append_log(self, task_id: str, message: str) -> None: ...
    def mark_running(self, task_id: str) -> None: ...
    def mark_completed(self, task_id: str, result: dict | None = None) -> None: ...
    def mark_failed(self, task_id: str, error: str) -> None: ...
```

要求：
- 单机单用户，先用进程内字典 + lock
- 当前任务规则：优先返回最新 `pending/running` 任务，否则返回最近完成任务；都没有则返回 idle payload
- 日志按列表存储，保留最近 N 条即可（例如 200）

- [ ] **Step 4: 在 `app.py` 中新增任务 API**

新增：

```python
@app.post("/api/tasks")
def create_task(payload: dict): ...

@app.get("/api/tasks/{task_id}")
def get_task(task_id: str): ...
```

并将 `GET /api/tasks/current` 改为读取 `TaskService.get_current_task()`。

- [ ] **Step 5: 跑测试到通过**

Run:

```bash
python3.11 -m pytest --no-cov webnovel-writer/dashboard/tests/test_phase2_tasks.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/app.py webnovel-writer/dashboard/task_service.py webnovel-writer/dashboard/tests/test_phase2_tasks.py
git commit -m "Persist live Phase 2 task state in the dashboard backend"
```

---

## Task 3: 接入 Claude 命令执行适配层

**Files:**
- Create: `webnovel-writer/dashboard/claude_runner.py`
- Modify: `webnovel-writer/dashboard/task_service.py`
- Test: `webnovel-writer/dashboard/tests/test_phase2_tasks.py`

- [ ] **Step 1: 写失败测试，锁定任务会从 pending 进入 completed/failed**

示例：

```python
def test_background_task_transitions_to_completed_when_runner_succeeds(...):
    ...
```

用 stub runner 先验证状态流转，不直接依赖真实 Claude 命令。

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 在 `claude_runner.py` 实现动作到命令的最小映射**

至少覆盖：
- `write_chapter`
- `review_chapter`
- `plan_outline`
- `inspect_setting`

约束：
- Phase 2 允许先把命令映射实现为 stub / echo / 明确占位 shell 命令，只要任务状态、日志、退出码链路真实可跑
- 若现有 skills/脚本命令已明确，可直接映射到真实命令
- 返回结构要统一为：
  - `success`
  - `exit_code`
  - `stdout`
  - `stderr`

- [ ] **Step 4: 在 `task_service.py` 中把创建任务接到后台执行**

要求：
- 创建任务后立刻返回
- 后台线程/worker 真正执行 runner
- 执行中写日志
- 成功标记 completed
- 失败标记 failed

- [ ] **Step 5: 跑测试到通过**

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/claude_runner.py webnovel-writer/dashboard/task_service.py webnovel-writer/dashboard/tests/test_phase2_tasks.py
git commit -m "Run Phase 2 workbench actions through a real task executor"
```

---

## Task 4: 扩展 SSE，推送任务事件而不是只推文件变更

**Files:**
- Modify: `webnovel-writer/dashboard/app.py`
- Modify: `webnovel-writer/dashboard/task_service.py`
- Test: `webnovel-writer/dashboard/tests/test_phase2_tasks.py`

- [ ] **Step 1: 写失败测试，锁定任务状态变更会写入事件流缓冲**

由于当前测试环境不适合直接跑完整 SSE 客户端，先测试 `task_service` 的事件广播接口，例如：

```python
def test_task_service_emits_event_payload_on_status_change(...):
    ...
```

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 在 `task_service.py` 增加订阅/广播接口**

至少实现：
- `subscribe_events()`
- `unsubscribe_events()`
- `emit_event()`

事件最小结构：

```json
{
  "type": "task.updated",
  "taskId": "...",
  "status": "running"
}
```

- [ ] **Step 4: 在 `app.py` 的 `/api/events` 中合并文件变更与任务事件**

要求：
- 不破坏现有文件变更 SSE
- 新增任务事件也能通过同一端点发出
- payload 中必须包含 `type`

- [ ] **Step 5: 跑测试到通过**

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/app.py webnovel-writer/dashboard/task_service.py webnovel-writer/dashboard/tests/test_phase2_tasks.py
git commit -m "Stream live task updates through the existing dashboard event channel"
```

---

## Task 5: 前端用真实任务 API 替换占位动作流

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/api.js`
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/data.js`
- Modify: `webnovel-writer/dashboard/frontend/tests/workbench.shell.test.mjs`

- [ ] **Step 1: 写失败测试，锁定任务卡模型能接受真实任务结构**

在 `workbench.shell.test.mjs` 或新建 `workbench.tasks.test.mjs` 中先写：

```js
test('buildRightSidebarModel preserves task logs and error state', async () => {
  ...
})
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
cd webnovel-writer/dashboard/frontend
node --test tests/workbench.shell.test.mjs tests/workbench.tasks.test.mjs
```

- [ ] **Step 3: 在 `api.js` 中增加真实任务接口封装**

新增：
- `createTask(action, context)`
- `fetchTask(taskId)`
- `cancelTask(taskId)`（如后端尚未做可先保留壳）

- [ ] **Step 4: 在 `App.jsx` 中替换当前前端 `setTimeout()` 模拟任务流**

要求：
- 点击动作卡 -> `POST /api/tasks`
- 任务返回后更新 `currentTask`
- 收到 SSE 中的 `task.updated` 事件时刷新当前任务
- 不再使用前端本地模拟完成

- [ ] **Step 5: 在 `data.js` 中补任务卡展示模型**

至少支持：
- `status`
- `task`
- `step`
- `updatedAt`
- `logs`
- `error`

- [ ] **Step 6: 跑前端测试到通过**

- [ ] **Step 7: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/api.js webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/data.js webnovel-writer/dashboard/frontend/tests
 git commit -m "Replace Phase 1 task stubs with live Phase 2 task orchestration"
```

---

## Task 6: 让右侧栏展示真实日志、失败原因与任务完成结果

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: `webnovel-writer/dashboard/frontend/tests/workbench.tasks.test.mjs`

- [ ] **Step 1: 写失败测试，锁定任务卡能渲染日志与错误状态**

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 在 `RightSidebar.jsx` 中补以下显示项**

- 最近任务日志（Top N）
- 失败原因
- 成功结果摘要
- 可选的“刷新页面”提示或自动刷新说明

- [ ] **Step 4: 在 `index.css` 中补运行态 / 成功态 / 失败态样式**

- [ ] **Step 5: 跑测试到通过**

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx webnovel-writer/dashboard/frontend/src/index.css webnovel-writer/dashboard/frontend/tests/workbench.tasks.test.mjs
git commit -m "Surface live task logs and failure states in the workbench sidebar"
```

---

## Task 7: 任务完成后刷新对应工作区

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`
- Test: manual end-to-end verification

- [ ] **Step 1: 在 `App.jsx` 中定义任务完成后的刷新策略**

规则建议：
- `write_chapter` / `review_chapter` -> 刷新章节页
- `plan_outline` -> 刷新大纲页
- `inspect_setting` -> 刷新设定页

- [ ] **Step 2: 为三个工作区提供显式刷新入口**

例如通过 `refreshToken` / `reloadKey` 传入页面组件。

- [ ] **Step 3: 当任务状态进入 `completed` 时触发对应页面刷新**

要求：
- 刷新只针对当前任务相关页面，不整页硬刷新
- 保持右栏消息和任务状态不丢失

- [ ] **Step 4: 手动验证三条主链**

验证：
1. 章节页 -> 聊天生成动作卡 -> 执行 -> 任务完成 -> 章节页刷新
2. 大纲页 -> 聊天生成动作卡 -> 执行 -> 任务完成 -> 大纲页刷新
3. 设定页 -> 聊天生成动作卡 -> 执行 -> 任务完成 -> 设定页刷新/提示更新

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx
git commit -m "Refresh the active workbench page when Phase 2 tasks finish"
```

---

## Task 8: 全量验证并写清 Phase 2 完成定义

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-web-workbench-design.md`（如有必要）
- Test: backend tests + frontend tests + build + manual runbook

- [ ] **Step 1: 跑后端测试**

```bash
python3.11 -m pytest --no-cov webnovel-writer/dashboard/tests/test_phase1_contracts.py webnovel-writer/dashboard/tests/test_phase2_tasks.py -q
```

Expected: 全部通过

- [ ] **Step 2: 跑前端测试与构建**

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard/frontend
node --test tests/workbench.data.test.mjs tests/workbench.shell.test.mjs tests/workbench.tasks.test.mjs
npm run build
```

Expected: 全部通过

- [ ] **Step 3: 启动服务并人工验收**

```bash
PYTHONPATH=/Users/liushuang/Projects/webnovel-writer/webnovel-writer python3.11 -m dashboard.server --project-root <project_root> --no-browser
```

人工验证：
- 动作卡点击后创建真实任务
- 任务卡从 pending -> running -> completed/failed
- 日志能实时或准实时显示
- 任务完成后页面刷新
- 未知 `GET /api/*` 不会误返回 SPA HTML

- [ ] **Step 4: 在 spec 或计划中补 “Phase 2 Done Means”**

至少明确：
- 动作卡不再是前端模拟
- 任务状态与日志来自真实后端任务流
- 任务完成会刷新对应工作区
- 聊天仍可为规则路由，但执行已是真任务链

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-12-web-workbench-design.md docs/superpowers/plans/2026-04-13-web-workbench-phase2.md
git commit -m "Document the Phase 2 completion bar for live workbench task execution"
```

---

## Self-Review

### Spec coverage
- 任务创建 / 状态 / 查询：Task 1-2 覆盖
- 真实执行链：Task 3 覆盖
- 日志/状态事件：Task 4 覆盖
- 前端动作卡接真任务：Task 5 覆盖
- 任务卡日志与失败态：Task 6 覆盖
- 完成后页面刷新：Task 7 覆盖
- Phase 2 验收：Task 8 覆盖

### Placeholder scan
- 未使用 TBD/TODO
- 每个任务都给出了精确文件、测试或运行命令
- 对尚不确定的 Claude 命令映射已明确允许先用 stub runner 验证任务链，而不是模糊跳过

### Type consistency
- 前后端统一使用 `createdAt / updatedAt`
- 任务状态统一使用 `idle / pending / running / completed / failed / cancelled`
- 动作类型统一沿用 Phase 1 的 `write_chapter / review_chapter / plan_outline / inspect_setting`

### Real-codebase fit check
- 计划默认继续使用当前单文件 `app.py` 路由入口，而非强推大规模拆包
- 计划默认复用现有 `RightSidebar.jsx` 与 `App.jsx` 状态接线
- 计划承认当前 SSE 只监听 `.webnovel` 的现实，并给出 Phase 2 的扩展策略
- 计划未要求引入新依赖或新前端状态库，符合当前仓库约束
