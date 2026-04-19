# Task 006: 前端 SkillFlowPanel 通用组件

## 目标

实现前端通用的 Skill 流程展示组件，能显示步骤进度、实时日志、表单输入。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/SkillFlowPanel.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/api.js`（修改，添加 skill API 函数）
- `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`（修改，添加测试入口）

## 依赖

- task-005（SSE skill 事件已就绪）

## 规格

### api.js 新增函数

```javascript
export function startSkill(skillName, options = {}) {
  return postJSON(`/api/skill/${skillName}/start`, options)
}

export function getSkillStatus(skillId) {
  return fetchJSON(`/api/skill/${skillId}/status`)
}

export function submitSkillStep(skillId, stepId, data) {
  return postJSON(`/api/skill/${skillId}/step`, { step_id: stepId, data })
}

export function cancelSkill(skillId) {
  return postJSON(`/api/skill/${skillId}/cancel`)
}
```

### SkillFlowPanel 组件

```jsx
<SkillFlowPanel
  skillId={activeSkillId}       // 当前 skill 实例 ID
  onCompleted={() => {}}        // 完成回调
  onCancelled={() => {}}        // 取消回调
/>
```

内部结构：
1. Step 进度条：横向步骤指示器，当前步骤高亮，已完成步骤打勾
2. 当前步骤面板：
   - `auto` 步骤：显示 spinner + 日志流
   - `form` 步骤：渲染动态表单（基于 step output_data 中的 schema）
   - `confirm` 步骤：显示结果 + 确认/取消按钮
3. 日志区域：滚动显示 skill.log 事件
4. 底部操作栏：取消按钮

### SSE 消费

监听现有 SSE 连接中的 `skill.step` / `skill.completed` / `skill.failed` / `skill.log` 事件，更新组件状态。

### OverviewPage 测试入口

在 ReadyState 中添加一个临时按钮"测试 Skill 流程"，点击后：
1. 调用 `startSkill("echo")`
2. 显示 SkillFlowPanel
3. echo skill 的 step_2 (confirm) 时显示确认按钮
4. 全部完成后显示成功提示

此按钮仅用于 Phase 0 验证，后续 Phase 会替换为真实 Skill 入口。

## TDD 验收

- Happy path：点击测试按钮 → 进度条从 Step 1 走到 Step 3 → 显示完成
- Edge case 1：Step 2 等待确认时，进度条停在 Step 2，显示确认按钮
- Edge case 2：取消按钮点击后，显示已取消状态
- Error case：后端返回错误时，显示错误信息而非白屏
