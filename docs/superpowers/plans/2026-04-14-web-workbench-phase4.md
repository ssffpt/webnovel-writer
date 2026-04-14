# Web Workbench Phase 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐工作台核心体验缺口：防止未保存数据丢失、失败任务可重试、任务完成后可跳转、页面切换时保留状态。

**Architecture:** 继续沿用现有 FastAPI + React/Vite 底座，不引入新依赖或状态管理库。前端在 `App.jsx` 层面增加导航守卫与状态缓存；后端无改动。

**Tech Stack:** React 19, Vite 6, 原生 fetch/EventSource, 现有 dashboard 结构

## Existing Dashboard Evolution Contract

- 修改主落点仍是前端 `src/` 目录下的文件
- 不引入 React Router、zustand、react-query 等新依赖
- 不改动后端 API，Phase 4 纯前端体验优化
- 复用 Phase 2/3 的任务链路、SSE 事件、聊天回流机制

## Recommended Execution Order and Risk Ranking

### P0：数据安全（防止未保存改动丢失）

1. **未保存改动导航守卫**
   - 风险：高
   - 原因：当前页面切换和关闭标签页都会静默丢失脏数据

2. **页面状态缓存**
   - 风险：中高
   - 原因：页面组件卸载后状态全部丢失，与导航守卫配合才有意义

### P1：任务闭环体验

3. **失败任务重试**
   - 风险：中
   - 原因：当前失败后只能重新输入聊天，没有直接重试入口

4. **任务完成后跳转提示**
   - 风险：中
   - 原因：当前只有文本提示，用户需手动导航

### P2：体验收口

5. **保存成功反馈增强**
   - 风险：低
   - 原因：当前"已同步"徽标太细微

6. **全局验证与 Phase 4 文档收口**
   - 风险：低

---

## Task 1: 未保存改动导航守卫

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`

- [ ] **Step 1: 在 `App.jsx` 添加 `beforeunload` 事件守卫**

当 `sidebarContext.dirty` 为 `true` 时，注册 `beforeunload` 事件阻止关闭/刷新：

```jsx
useEffect(() => {
  const handler = (e) => {
    if (sidebarContext.dirty) {
      e.preventDefault()
      e.returnValue = ''
    }
  }
  window.addEventListener('beforeunload', handler)
  return () => window.removeEventListener('beforeunload', handler)
}, [sidebarContext.dirty])
```

- [ ] **Step 2: 在页面切换时检查 dirty 状态**

修改 TopBar 的 `onSelectPage` 回调：

```jsx
const handleSelectPage = useCallback((page) => {
  if (sidebarContext.dirty && !window.confirm('当前页面有未保存的修改，确定要离开吗？')) {
    return
  }
  setWorkbenchState(prev => ({ ...prev, page }))
}, [sidebarContext.dirty])
```

- [ ] **Step 3: 在同页面内切换文件时检查 dirty 状态**

为三个编辑页面的 `onSelectFile` 回调增加确认逻辑。在每个 Page 组件中，选中新文件前检查 `dirty`：

```jsx
function handleSelectFile(path) {
  if (dirty && !window.confirm('当前文件有未保存的修改，切换文件将丢失修改。确定继续？')) {
    return
  }
  setSelectedPath(path)
}
```

- [ ] **Step 4: 手动验证**

1. 编辑正文 → 刷新页面 → 浏览器弹出确认
2. 编辑正文 → 点击大纲页 → 弹出确认 → 取消后留在当前页
3. 编辑正文 → 点击大纲页 → 确认 → 切换成功

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx
git commit -m "Guard against losing unsaved changes on navigation and close"
```

---

## Task 2: 页面切换时保留编辑状态

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`

- [ ] **Step 1: 将三个编辑页的选中路径和脏状态提升到 `App.jsx`**

在 `App.jsx` 中增加页面状态缓存：

```jsx
const [pageState, setPageState] = useState({
  chapters: { selectedPath: null, dirty: false },
  outline: { selectedPath: null, dirty: false },
  settings: { selectedPath: null, dirty: false },
})
```

- [ ] **Step 2: 将缓存状态通过 props 传入各页面**

```jsx
<ChapterPage
  {...pageProps}
  cachedSelectedPath={pageState.chapters.selectedPath}
  onStateChange={(s) => setPageState(prev => ({ ...prev, chapters: { ...prev.chapters, ...s } }))}
/>
```

- [ ] **Step 3: 各页面组件优先使用缓存状态**

如果 `cachedSelectedPath` 存在且文件树中仍有该文件，则优先选中它，而非默认选第一个。

- [ ] **Step 4: 各页面组件在选中/脏状态变更时通知 App**

通过 `onStateChange({ selectedPath, dirty })` 回调。

- [ ] **Step 5: 手动验证**

1. 在章节页选中第3章 → 切换到总览 → 切回章节页 → 第3章仍被选中
2. 编辑内容（dirty=true）→ 切换页面 → 切回 → 编辑内容保留（需配合 Task 1 的确认逻辑）

- [ ] **Step 6: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx
git commit -m "Preserve editor state across workbench page switches"
```

---

## Task 3: 失败任务重试

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`

- [ ] **Step 1: 在 `App.jsx` 中存储最近一次执行的 action**

新增 ref：
```jsx
const lastActionRef = useRef(null)
```

在 `handleRunAction` 中保存：
```jsx
lastActionRef.current = action
```

- [ ] **Step 2: 在 `RightSidebar.jsx` 任务卡中增加重试按钮**

当 `currentTask.status === 'failed'` 时显示"重试"按钮：

```jsx
{model.currentTask.status === 'failed' && onRetryAction && (
  <button type="button" className="workbench-primary-button" onClick={onRetryAction}>
    重试
  </button>
)}
```

- [ ] **Step 3: 在 `App.jsx` 中实现 `handleRetryAction`**

```jsx
const handleRetryAction = useCallback(() => {
  if (lastActionRef.current) {
    handleRunAction(lastActionRef.current)
  }
}, [handleRunAction])
```

- [ ] **Step 4: 手动验证**

1. 创建 force_fail 任务 → 任务失败 → 点击重试 → 再次执行

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Add retry button for failed workbench tasks"
```

---

## Task 4: 任务完成后跳转提示

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/App.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`

- [ ] **Step 1: 在任务完成回流消息中增加可点击的跳转链接**

修改 SSE handler 中 completed 消息的 reason 构建：如果当前不在目标页面，在聊天消息中增加 `navigateTo` 字段。

```jsx
{
  role: 'assistant',
  kind: 'task-success',
  content: `${task.action?.label || '任务'} 已完成。`,
  reason: buildCompletionReason(activePage, targetPage, task.result?.summary),
  scope: { page: sidebarContext?.page, selectedPath: sidebarContext?.selectedPath },
  navigateTo: activePage !== targetPage ? targetPage : null,
}
```

- [ ] **Step 2: 在 `RightSidebar.jsx` 中渲染跳转按钮**

当消息包含 `navigateTo` 时，显示"前往查看"按钮：

```jsx
{message.navigateTo && (
  <button
    type="button"
    className="workbench-nav-button"
    onClick={() => onNavigateToPage?.(message.navigateTo)}
  >
    前往{pageLabel(message.navigateTo)}查看
  </button>
)}
```

- [ ] **Step 3: 在 `App.jsx` 中提供 `handleNavigateToPage`**

```jsx
const handleNavigateToPage = useCallback((page) => {
  setWorkbenchState(prev => ({ ...prev, page }))
}, [])
```

传入 `RightSidebar`。

- [ ] **Step 4: 手动验证**

1. 在总览页执行章节写作任务 → 完成后聊天区出现"前往章节页查看"按钮 → 点击跳转

- [ ] **Step 5: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/App.jsx webnovel-writer/dashboard/frontend/src/workbench/RightSidebar.jsx webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Add navigation links in chat after cross-page task completion"
```

---

## Task 5: 保存成功反馈增强

**Files:**
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`
- Modify: `webnovel-writer/dashboard/frontend/src/index.css`

- [ ] **Step 1: 在三个编辑页面保存成功后显示短暂的成功提示**

保存成功时，设置 `saveState = 'saved'`，2 秒后自动恢复为 `'idle'`：

```jsx
const handleSave = async () => {
  setSaveState('saving')
  try {
    await saveFile(selectedPath, draft)
    setDirty(false)
    setSaveState('saved')
    setTimeout(() => setSaveState('idle'), 2000)
  } catch (err) {
    setSaveState('error')
    setContentError(err.message)
  }
}
```

- [ ] **Step 2: 在 CSS 中增加保存成功样式**

```css
.save-badge.saved {
  background: var(--accent-green);
  color: white;
}
```

状态徽标显示逻辑：
- `idle` → 无徽标
- `dirty` → "未保存"（amber）
- `saving` → "保存中..."（blue）
- `saved` → "已保存"（green，2秒后消失）
- `error` → "保存失败"（red）

- [ ] **Step 3: 手动验证**

1. 编辑内容 → 点击保存 → "已保存" 绿色徽标出现 → 2秒后消失

- [ ] **Step 4: Commit**

```bash
git add webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx webnovel-writer/dashboard/frontend/src/index.css
git commit -m "Add save success feedback with auto-dismiss badge"
```

---

## Task 6: 全量验证并补写 Phase 4 完成定义

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-web-workbench-design.md`
- Test: frontend build + all backend/frontend tests + manual runbook

- [ ] **Step 1: 跑全部后端测试**

```bash
python3.11 -m pytest --no-cov webnovel-writer/dashboard/tests/ -q
```

- [ ] **Step 2: 跑前端测试与构建**

```bash
cd webnovel-writer/dashboard/frontend
node --test tests/workbench.*.test.mjs
npm run build
```

- [ ] **Step 3: 启动服务并人工验收**

验证：
- 编辑内容 → 刷新/切换页面 → 弹出确认
- 页面切换后切回 → 选中状态保留
- 任务失败 → 可重试
- 任务完成 → 聊天区有跳转按钮
- 保存成功 → 绿色徽标出现后消失

- [ ] **Step 4: 在 spec 中补 "Phase 4 Done Means"**

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/specs/2026-04-12-web-workbench-design.md docs/superpowers/plans/2026-04-14-web-workbench-phase4.md
git commit -m "Document the Phase 4 completion bar for workbench UX improvements"
```

---

## Self-Review

### Spec coverage
- 未保存改动守卫：Task 1 覆盖
- 页面状态缓存：Task 2 覆盖
- 失败任务重试：Task 3 覆盖
- 任务完成跳转：Task 4 覆盖
- 保存反馈增强：Task 5 覆盖
- 全量验收：Task 6 覆盖

### Out of scope for Phase 4
- 草稿对比/diff（需要引入 diff 库，Phase 4 不做）
- 受影响章节提示（需要后端支持，Phase 4 不做）
- React Error Boundary（非核心体验，可后续补充）
- Toast/通知系统（Phase 4 用 chat 回流消息替代）

### Type consistency
- 页面状态缓存结构：`{ selectedPath: string | null, dirty: boolean }`
- 任务重试复用 `handleRunAction`，无新 API
- 导航跳转使用现有 `setWorkbenchState` page 字段
