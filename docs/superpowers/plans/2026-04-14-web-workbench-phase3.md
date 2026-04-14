# Web Workbench Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前“规则聊天 + 动作卡创建任务”的基础能力升级为真正的聊天助手工作流：让聊天建议更贴合当前页面与当前文件，执行后能给出更清晰的结果反馈、跳转与联动提示。

**Architecture:** 继续沿用现有 FastAPI + React/Vite + dashboard 单应用结构，不新增独立聊天服务。后端在现有 `POST /api/chat` 基础上增强上下文感知与动作建议生成；前端继续复用 `RightSidebar.jsx` 作为聊天入口，在 `App.jsx` 中统一维护聊天记录、建议动作与任务结果回流。Phase 3 的重点不是另起一套大模型平台，而是在现有 Phase 2 任务链之上，把“聊天理解 → 建议动作 → 执行结果回流”这条用户感知路径做顺。

**Tech Stack:** FastAPI, React 19, Vite 6, Python pathlib/json, 原生 fetch/EventSource, 现有 dashboard/task_service/workbench_service 结构

## Existing Dashboard Evolution Contract

本计划默认 **在现有 dashboard 基础上演进**，不是新建独立前后端项目。执行时必须遵守以下约束：

- 修改主落点仍是 `webnovel-writer/dashboard/app.py`、`webnovel-writer/dashboard/workbench_service.py`、`webnovel-writer/dashboard/frontend/src/`
- 不新建独立聊天后端或额外前端状态库，继续在当前 `App.jsx + RightSidebar.jsx` 基础上增强
- 复用 Phase 2 的任务 API、SSE 任务事件与页面刷新机制，不重做任务系统
- Phase 3 的目标是“聊天助手真正变得可用”，不是提前进入 Phase 4 的大规模体验重构

## Real-Codebase Execution Notes

基于当前仓库真实状态，Phase 3 执行时必须注意：

- 当前 `POST /api/chat` 仍是规则映射，且主要依赖 `message` 文本关键词；Phase 3 应在此基础上增强上下文输入，不应改成不可控的黑盒返回。
- 当前前端 `sidebarContext` 已经包含 `page / selectedPath / dirty`，这是 Phase 3 最重要的输入来源，应优先复用，而不是重新收集一套上下文。
- 当前动作卡执行链已经是“真实任务 API + SSE 更新”；Phase 3 不需要再扩任务基础设施，重点是聊天生成更准确的动作卡，以及任务完成后的聊天回流。
- 当前 `RightSidebar.jsx` 已同时承载聊天输入、动作卡、任务卡。Phase 3 可以继续增强其显示逻辑，但不应拆出新的聊天面板体系。
- 当前 `workbench_service.py` 已经负责 summary/save/chat helper；如果继续增强 `POST /api/chat`，优先把策略函数放进 `workbench_service.py` 或其紧邻 helper，而不是再次散落到 `app.py`。
- 当前前端没有专门的“建议动作来源说明”或“聊天建议理由”，Phase 3 应补上轻量解释字段，帮助用户理解为什么推荐这个动作。

## Recommended Execution Order and Risk Ranking

### P0：阻塞型前置项

1. **定义聊天响应契约的增强字段**
   - 涉及：回复文本、建议动作、建议理由、适用页面、推荐优先级
   - 风险：高
   - 原因：没有稳定契约，前后端会在聊天显示层反复对不齐

2. **锁定“当前页面 + 当前文件”上下文输入**
   - 涉及：`sidebarContext`、页面选中文件、dirty 状态
   - 风险：高
   - 原因：Phase 3 的价值就是“聊天知道你正在看什么、改什么”

### P1：主干增强

3. **后端 `POST /api/chat` 增强为上下文感知建议**
   - 风险：高
   - 目标：同一句话在不同页面、不同选中文件下给出不同动作建议

4. **前端聊天记录结构增强**
   - 风险：中高
   - 目标：把聊天中的“建议动作来源、推荐理由、执行结果”也纳入消息流，不只是一句普通文本回复

5. **动作卡与聊天消息联动**
   - 风险：中高
   - 目标：用户点击动作卡后，聊天区应出现“已创建任务 / 已完成 / 失败”的回流消息

### P2：体验收口

6. **任务完成后的跳转/提示策略**
   - 风险：中
   - 目标：例如大纲规划完成后提示“可前往大纲页查看”，而不是静默更新

7. **空状态与错误状态优化**
   - 风险：中
   - 目标：聊天失败、无建议动作、上下文不足时，给出用户可理解的提示

### P3：验证与审核

8. **端到端人工验收与 Phase 3 文档收口**
   - 风险：中

## File Structure

### Backend
- Modify: `webnovel-writer/dashboard/app.py` — 继续复用 `POST /api/chat`，但返回增强后的聊天响应结构
- Modify: `webnovel-writer/dashboard/workbench_service.py` — 增加基于页面/路径/脏状态的聊天建议策略函数
- Modify: `webnovel-writer/dashboard/tests/test_phase2_tasks.py`（如需复用 helper）
- Create: `webnovel-writer/dashboard/tests/test_phase3_chat.py` — 锁定上下文感知聊天建议

### Frontend
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx` — 维护增强版聊天记录、动作执行回流消息、跳转/刷新提示
- Modify: `webnovel-writer/dashboard/frontend/src/api.js` — 保持 `sendChat()` 接口，但兼容更丰富的响应结构
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/data.js` — 增加聊天消息/动作建议/结果说明的模型转换函数
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx` — 增强聊天展示、建议理由、结果回流
- Modify: `webnovel-writer/dashboard/frontend/src/index.css` — 聊天消息类型、建议说明、结果提示样式
- Create: `webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs`

### Verification / Docs
- Modify: `docs/superpowers/specs/2026-04-12-web-workbench-design.md` — 如实现中对聊天交互模型有明确收敛，补充到设计文档
- Create: `docs/superpowers/plans/2026-04-14-web-workbench-phase3.md`
- Test manually: `python3.11 -m dashboard.server --project-root <project_root> --no-browser`
- Test manually: `cd webnovel-writer/dashboard/frontend && npm run build`

---

## Task 1: 定义 Phase 3 聊天响应契约

**Files:**
- Create: `webnovel-writer/dashboard/tests/test_phase3_chat.py`
- Modify: `webnovel-writer/dashboard/workbench_service.py`

- [ ] **Step 1: 写第一条失败测试，锁定聊天响应增强字段**

在 `test_phase3_chat.py` 中先写：

```python
def test_chat_response_includes_reason_and_scope_for_outline_page(...):
    ...
```

断言至少包含：
- `reply`
- `suggested_actions`
- `reason`
- `scope.page`
- `scope.selectedPath`

- [ ] **Step 2: 运行测试，确认先失败**

Run:

```bash
python3.11 -m pytest --no-cov webnovel-writer/dashboard/tests/test_phase3_chat.py -q
```

Expected: FAIL，原因是当前 `/api/chat` 返回结构过于简单。

- [ ] **Step 3: 在 `workbench_service.py` 中定义增强版聊天响应 helper**

至少补：

```python
def build_chat_response(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    ...
```

增强返回字段：
- `reply`
- `suggested_actions`
- `reason`
- `scope`

- [ ] **Step 4: Commit**

```bash
git add webnovel-writer/dashboard/workbench_service.py webnovel-writer/dashboard/tests/test_phase3_chat.py
git commit -m "Define the Phase 3 chat response contract"
```

---

## Task 2: 后端让聊天建议感知页面与当前文件

**Files:**
- Modify: `webnovel-writer/dashboard/workbench_service.py`
- Modify: `webnovel-writer/dashboard/app.py`
- Test: `webnovel-writer/dashboard/tests/test_phase3_chat.py`

- [ ] **Step 1: 写失败测试，锁定同一消息在不同页面下给出不同建议**

例如：

```python
def test_same_message_routes_to_different_actions_by_page_context(...):
    ...
```

示例断言：
- 在 `outline` 页输入“帮我继续” -> 更倾向 `plan_outline`
- 在 `chapters` 页输入“帮我继续” -> 更倾向 `write_chapter`

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 在 `build_chat_response()` 中加入页面上下文规则**

要求：
- `page=chapters` 时优先建议章节类动作
- `page=outline` 时优先建议大纲类动作
- `page=settings` 时优先建议设定检查/整理类动作
- `selectedPath` 存在时，把路径写入动作 params
- `dirty=true` 时避免建议“立即执行高风险动作”，优先提示先保存

- [ ] **Step 4: 跑测试到通过**

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/app.py webnovel-writer/dashboard/workbench_service.py webnovel-writer/dashboard/tests/test_phase3_chat.py
git commit -m "Make Phase 3 chat suggestions aware of the active page and file"
```

---

## Task 3: 前端聊天模型支持建议理由与作用范围

**Files:**
- Create: `webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/data.js`

- [ ] **Step 1: 写失败测试，锁定聊天消息与动作建议模型转换**

在 `workbench.chat.test.mjs` 中先写：

```js
test('buildChatReplyModel preserves reason and scope', async () => {
  ...
})
```

断言至少包含：
- `reply`
- `reason`
- `scope.page`
- `scope.selectedPath`
- `suggestedActions`

- [ ] **Step 2: 运行测试，确认失败**

Run:

```bash
cd webnovel-writer/dashboard/frontend
node --test tests/workbench.chat.test.mjs
```

- [ ] **Step 3: 在 `data.js` 中补聊天响应建模函数**

例如：

```js
export function buildChatReplyModel(response, fallbackContext) {
  ...
}
```

- [ ] **Step 4: 跑测试到通过**

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/workbench/data.js webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs
git commit -m "Model Phase 3 chat replies with explicit reason and scope"
```

---

## Task 4: 前端聊天区显示“建议理由 + 作用范围”

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`
- Test: `webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs`

- [ ] **Step 1: 写失败测试，锁定聊天响应能显示 reason/scope**

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 在 `App.jsx` 中接入增强版聊天响应结构**

要求：
- 聊天发送后除了追加 assistant 文本，还要保留：
  - `reason`
  - `scope`
  - `suggested_actions`
- 不丢失原来的消息列表结构

- [ ] **Step 4: 在 `RightSidebar.jsx` 中显示建议理由与作用范围**

例如显示：
- “推荐原因：当前位于大纲页，且已选中卷一文件”
- “作用范围：大纲 / 卷一.md”

- [ ] **Step 5: 在 `index.css` 中补说明文案样式**

- [ ] **Step 6: 跑测试到通过**

- [ ] **Step 7: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx webnovel-writer/dashboard/frontend/src/index.css webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs
git commit -m "Explain why each Phase 3 chat suggestion applies to the current workbench context"
```

---

## Task 5: 动作执行结果回流到聊天记录

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Test: `webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs`

- [ ] **Step 1: 写失败测试，锁定任务完成/失败后会生成回流消息**

例如：

```js
test('createTask result is mirrored back into chat messages', async () => {
  ...
})
```

- [ ] **Step 2: 运行测试，确认失败**

- [ ] **Step 3: 在 `App.jsx` 中补任务事件到聊天消息的桥接**

要求：
- `task.updated` 进入 `completed` 时，追加一条 assistant 回流消息
- `task.updated` 进入 `failed` 时，也追加一条失败回流消息
- 回流消息至少包含：
  - 动作名
  - 结果摘要 / 错误

- [ ] **Step 4: 跑测试到通过**

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx webnovel-writer/dashboard/frontend/tests/workbench.chat.test.mjs
git commit -m "Mirror Phase 3 task outcomes back into the chat transcript"
```

---

## Task 6: 聊天结果提示与页面联动优化

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Test: manual verification

- [ ] **Step 1: 当聊天建议动作成功完成时，给出明确提示**

要求：
- 如果当前不在相关页面，提示“可前往章节页/大纲页/设定页查看结果”
- 如果当前就在相关页面，提示“已刷新当前页面”

- [ ] **Step 2: dirty 状态下的聊天建议要更谨慎**

要求：
- 若当前页面 `dirty=true`，聊天回复应优先提醒先保存，而不是直接鼓励执行高风险动作

- [ ] **Step 3: 手动验证三条聊天驱动主链**

验证：
1. 在章节页选中文件后输入“帮我继续”，应推荐章节类动作
2. 在大纲页选中文件后输入“帮我继续”，应推荐大纲类动作
3. 在设定页修改后未保存时输入“帮我检查”，应优先提示先保存或明确风险

- [ ] **Step 4: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx
git commit -m "Align Phase 3 chat guidance with current page state and save risk"
```

---

## Task 7: 全量验证并补写 Phase 3 完成定义

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-web-workbench-design.md`（如有必要）
- Modify: `docs/superpowers/plans/2026-04-14-web-workbench-phase3.md`
- Test: backend tests + frontend tests + build + manual runbook

- [ ] **Step 1: 跑后端测试**

```bash
python3.11 -m pytest --no-cov webnovel-writer/dashboard/tests/test_phase1_contracts.py webnovel-writer/dashboard/tests/test_phase2_tasks.py webnovel-writer/dashboard/tests/test_phase3_chat.py -q
```

Expected: 全部通过

- [ ] **Step 2: 跑前端测试与构建**

```bash
cd /Users/liushuang/Projects/webnovel-writer/webnovel-writer/dashboard/frontend
node --test tests/workbench.data.test.mjs tests/workbench.shell.test.mjs tests/workbench.tasks.test.mjs tests/workbench.chat.test.mjs
npm run build
```

Expected: 全部通过

- [ ] **Step 3: 启动服务并人工验收**

```bash
PYTHONPATH=/Users/liushuang/Projects/webnovel-writer/webnovel-writer python3.11 -m dashboard.server --project-root <project_root> --no-browser
```

人工验证：
- 同一句聊天在不同页面给出不同动作建议
- 建议理由与作用范围可见
- 任务完成后聊天区有回流消息
- 页面刷新提示准确
- 未保存状态下聊天建议不会误导执行

- [ ] **Step 4: 在计划或 spec 中补 “Phase 3 Done Means”**

至少明确：
- 聊天建议已感知当前页面与当前文件
- 建议动作有理由说明，不是黑盒推荐
- 任务完成/失败会回流到聊天记录
- 聊天与工作区形成完整闭环

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-12-web-workbench-design.md docs/superpowers/plans/2026-04-14-web-workbench-phase3.md
git commit -m "Document the Phase 3 completion bar for chat-driven workbench guidance"
```

---

## Self-Review

### Spec coverage
- 聊天响应增强字段：Task 1 覆盖
- 页面/路径感知建议：Task 2 覆盖
- 前端聊天建模：Task 3 覆盖
- 建议理由与作用范围展示：Task 4 覆盖
- 任务结果回流聊天记录：Task 5 覆盖
- 聊天与页面状态联动：Task 6 覆盖
- Phase 3 验收与文档收口：Task 7 覆盖

### Placeholder scan
- 未使用 TBD/TODO
- 每个任务都给出明确文件与运行命令
- 没有把“聊天更智能”写成空泛目标，而是拆成可验证的结构字段与联动行为

### Type consistency
- 前端继续使用 `updatedAt`
- 聊天响应统一至少包含 `reply / suggested_actions / reason / scope`
- 动作类型继续沿用 Phase 2：`write_chapter / review_chapter / plan_outline / inspect_setting`

### Real-codebase fit check
- 计划默认继续使用现有 `POST /api/chat`，而不是引入新聊天后端
- 计划继续复用 `RightSidebar.jsx` 与 `App.jsx` 现有状态结构
- 计划不要求引入新依赖或状态管理库，符合当前仓库约束
