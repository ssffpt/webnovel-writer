# Task 308: WriteFlow 前端组件 + ChapterPage 集成

## 目标

实现 WriteFlow 前端组件，嵌入 ChapterPage，用户可在章节页选择"AI 创作"模式启动写作流程。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/WriteFlow.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`（修改）
- `webnovel-writer/dashboard/frontend/src/api.js`（修改，如需新增）

## 依赖

- task-307（后端 WriteSkillHandler 全部步骤完成）
- Phase 0 task-006（SkillFlowPanel 已存在）

## 前置知识

api.js 中已有的 Skill API 函数：

```javascript
export function startSkill(skillName, options = {}) { ... }
export function getSkillStatus(skillId) { ... }
export function submitSkillStep(skillId, stepId, data) { ... }
export function cancelSkill(skillId) { ... }
```

ChapterPage 当前结构：左侧文件列表 + 右侧 textarea 编辑器 + 专注模式。

## 规格

### WriteFlow 组件

```jsx
import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel'
import { startSkill } from '../api'

/**
 * 章节创作流程面板，嵌入 ChapterPage。
 *
 * Props:
 *   projectRoot: string — 项目根目录
 *   chapterNum: number — 章节编号
 *   onCompleted(text: string) — 创作完成回调，传回最终正文
 *   onCancelled() — 取消回调
 */
export default function WriteFlow({ projectRoot, chapterNum, onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)
  const [mode, setMode] = useState('standard')

  const handleStart = async () => {
    const result = await startSkill('write', {
      project_root: projectRoot,
      chapter_num: chapterNum,
      mode: mode,
    })
    setSkillId(result.id)
  }

  if (!skillId) {
    return (
      <WriteStartScreen
        chapterNum={chapterNum}
        mode={mode}
        onModeChange={setMode}
        onStart={handleStart}
      />
    )
  }

  return (
    <SkillFlowPanel
      skillId={skillId}
      stepRenderers={WRITE_STEP_RENDERERS}
      onCompleted={(finalState) => {
        const text = finalState?.final_text || ''
        onCompleted(text)
      }}
      onCancelled={onCancelled}
    />
  )
}
```

### WriteStartScreen

```jsx
function WriteStartScreen({ chapterNum, mode, onModeChange, onStart }) {
  return (
    <div className="write-start-screen">
      <h3>AI 创作 — 第{chapterNum}章</h3>
      <div className="mode-selector">
        <label>创作模式：</label>
        <select value={mode} onChange={e => onModeChange(e.target.value)}>
          <option value="standard">标准模式（完整 6 步）</option>
          <option value="fast">快速模式（跳过风格适配）</option>
          <option value="minimal">极简模式（仅核心审查）</option>
        </select>
        <p className="mode-hint">
          {mode === 'standard' && '完整流程：起草 → 风格适配 → 六维审查 → 润色'}
          {mode === 'fast' && '快速流程：起草 → 六维审查 → 润色（跳过风格适配）'}
          {mode === 'minimal' && '极简流程：起草 → 核心审查(3项) → 润色'}
        </p>
      </div>
      <button className="btn-primary" onClick={onStart}>
        开始创作
      </button>
    </div>
  )
}
```

### stepRenderers

```javascript
const WRITE_STEP_RENDERERS = {
  step_1: ContextAgentDisplay,    // Context Agent（auto，显示加载结果）
  step_2a: DraftConfirm,          // 正文起草（confirm，预览+编辑）
  step_2b: StyleAdaptConfirm,     // 风格适配（confirm，diff 对比）
  step_3: ReviewResultsDisplay,   // 六维审查（auto，雷达图+问题列表）
  step_4: PolishConfirm,          // 润色（confirm，diff+编辑）
  step_5: DataAgentDisplay,       // Data Agent（auto，处理结果）
  step_6: GitBackupDisplay,       // Git 备份（auto，提交结果）
}
```

### Step 1 — ContextAgentDisplay

```jsx
function ContextAgentDisplay({ stepState }) {
  const data = stepState.output_data || {}
  return (
    <div className="context-agent-display">
      <h4>Context Agent</h4>
      <p>{data.instruction || '正在构建上下文...'}</p>
      {data.rag_mode === 'degraded' && (
        <p className="warning">RAG 未配置，使用文件系统降级模式</p>
      )}
      {data.task_brief && (
        <details>
          <summary>任务书详情</summary>
          <ul>
            <li>本章大纲：{data.task_brief.chapter_outline ? '已加载' : '无'}</li>
            <li>前文摘要：{data.task_brief.previous_summaries?.length || 0} 章</li>
            <li>相关设定：{data.task_brief.relevant_settings ? '已加载' : '无'}</li>
            <li>待回收伏笔：{data.task_brief.pending_foreshadowing?.length || 0} 条</li>
          </ul>
        </details>
      )}
    </div>
  )
}
```

### Step 2A — DraftConfirm

```jsx
function DraftConfirm({ stepState, onSubmit }) {
  const { draft_text, word_count } = stepState.output_data || {}
  const [editedText, setEditedText] = useState(draft_text || '')
  const [isEditing, setIsEditing] = useState(false)

  return (
    <div className="draft-confirm">
      <h4>正文草稿</h4>
      <p className="word-count">字数：{word_count || 0}</p>

      {isEditing ? (
        <textarea
          className="draft-editor"
          value={editedText}
          onChange={e => setEditedText(e.target.value)}
          rows={20}
        />
      ) : (
        <div className="draft-preview">
          <pre>{draft_text}</pre>
        </div>
      )}

      <div className="confirm-actions">
        <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>
          确认草稿
        </button>
        {!isEditing ? (
          <button className="btn-secondary" onClick={() => setIsEditing(true)}>
            编辑修改
          </button>
        ) : (
          <button
            className="btn-secondary"
            onClick={() => onSubmit({ confirmed: false, edited_text: editedText })}
          >
            提交修改
          </button>
        )}
      </div>
    </div>
  )
}
```

### Step 2B — StyleAdaptConfirm

```jsx
function StyleAdaptConfirm({ stepState, onSubmit }) {
  const { adapted_text, has_changes, changes_summary } = stepState.output_data || {}
  const [feedback, setFeedback] = useState('')

  return (
    <div className="style-adapt-confirm">
      <h4>风格适配</h4>
      <p>{changes_summary}</p>

      {has_changes ? (
        <div className="diff-view">
          <p className="diff-hint">高亮部分为风格调整</p>
          <pre>{adapted_text}</pre>
        </div>
      ) : (
        <p>无需风格调整</p>
      )}

      <div className="confirm-actions">
        <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>
          确认
        </button>
        <div className="feedback-input">
          <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="修改意见" />
          <button
            className="btn-secondary"
            onClick={() => onSubmit({ confirmed: false, feedback })}
            disabled={!feedback}
          >
            提交意见
          </button>
        </div>
      </div>
    </div>
  )
}
```

### Step 3 — ReviewResultsDisplay

```jsx
function ReviewResultsDisplay({ stepState }) {
  const { review_results, total_score, issues_count, critical_count } = stepState.output_data || {}

  return (
    <div className="review-results-display">
      <h4>六维审查</h4>
      <div className="score-summary">
        <span className="total-score">总分：{total_score}/10</span>
        <span className="issues-count">{issues_count} 个问题</span>
        {critical_count > 0 && <span className="critical-badge">{critical_count} 个严重问题</span>}
      </div>

      <div className="dimension-scores">
        {(review_results || []).map(r => (
          <div key={r.dimension} className={`dimension-row ${r.passed ? 'passed' : 'failed'}`}>
            <span className="dim-name">{r.dimension}</span>
            <div className="score-bar">
              <div className="score-fill" style={{ width: `${r.score * 10}%` }} />
            </div>
            <span className="dim-score">{r.score}</span>
          </div>
        ))}
      </div>

      {issues_count > 0 && (
        <details>
          <summary>问题详情</summary>
          {(review_results || []).flatMap(r => r.issues || []).map((issue, i) => (
            <div key={i} className={`issue-item severity-${issue.severity}`}>
              <span className="severity-badge">{issue.severity}</span>
              <span className="issue-message">{issue.message}</span>
              {issue.suggestion && <p className="issue-suggestion">{issue.suggestion}</p>}
            </div>
          ))}
        </details>
      )}
    </div>
  )
}
```

### Step 4 — PolishConfirm

```jsx
function PolishConfirm({ stepState, onSubmit }) {
  const { polished_text, fix_report, has_changes, word_count } = stepState.output_data || {}
  const [editedText, setEditedText] = useState(polished_text || '')
  const [isEditing, setIsEditing] = useState(false)

  return (
    <div className="polish-confirm">
      <h4>润色结果</h4>
      {fix_report && (
        <div className="fix-report">
          <span>修复：{fix_report.critical_fixed} critical / {fix_report.high_fixed} high</span>
          <span>Anti-AI：{fix_report.anti_ai_fixes} 处</span>
        </div>
      )}
      <p className="word-count">字数：{word_count || 0}</p>

      {isEditing ? (
        <textarea className="polish-editor" value={editedText} onChange={e => setEditedText(e.target.value)} rows={20} />
      ) : (
        <pre className="polish-preview">{polished_text}</pre>
      )}

      <div className="confirm-actions">
        <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>确认</button>
        {!isEditing ? (
          <button className="btn-secondary" onClick={() => setIsEditing(true)}>编辑修改</button>
        ) : (
          <button className="btn-secondary" onClick={() => onSubmit({ confirmed: false, edited_text: editedText })}>
            提交修改
          </button>
        )}
      </div>
    </div>
  )
}
```

### Step 5/6 — DataAgentDisplay / GitBackupDisplay

```jsx
function DataAgentDisplay({ stepState }) {
  const results = stepState.output_data?.results || {}
  return (
    <div className="data-agent-display">
      <h4>Data Agent</h4>
      <ul>
        <li>正文已保存：{results.chapter_saved ? '是' : '处理中...'}</li>
        <li>实体提取：{results.entities_extracted ?? '...'} 个</li>
        <li>摘要生成：{results.summary_generated ? '完成' : '...'}</li>
        <li>场景切片：{results.scenes_sliced ?? '...'} 个</li>
        <li>债务检测：{results.debts_detected ?? '...'} 条</li>
      </ul>
    </div>
  )
}

function GitBackupDisplay({ stepState }) {
  const data = stepState.output_data || {}
  if (data.skipped) {
    return <p className="git-skipped">Git 备份已跳过（{data.reason}）</p>
  }
  return (
    <div className="git-backup-display">
      {data.success
        ? <p className="git-success">Git 提交成功：{data.commit_hash}</p>
        : <p className="git-error">Git 提交失败：{data.error}（不影响流程）</p>
      }
    </div>
  )
}
```

### ChapterPage 集成

修改 `ChapterPage.jsx`，新增模式切换：

```jsx
import WriteFlow from './WriteFlow'

// 在组件内部
const [editMode, setEditMode] = useState('manual') // 'manual' | 'ai'

// 编辑器顶部新增模式切换
<div className="mode-toggle">
  <button
    className={editMode === 'manual' ? 'active' : ''}
    onClick={() => setEditMode('manual')}
  >
    手动编辑
  </button>
  <button
    className={editMode === 'ai' ? 'active' : ''}
    onClick={() => setEditMode('ai')}
  >
    AI 创作
  </button>
</div>

// 根据模式渲染不同内容
{editMode === 'ai' ? (
  <WriteFlow
    projectRoot={projectRoot}
    chapterNum={currentChapterNum}
    onCompleted={(text) => {
      // 创作完成，加载正文到编辑器
      setEditMode('manual')
      setEditorContent(text)
    }}
    onCancelled={() => setEditMode('manual')}
  />
) : (
  // 原有的 textarea 编辑器
  <textarea value={editorContent} onChange={...} />
)}
```

## TDD 验收

- Happy path：ChapterPage 切换到"AI 创作" → WriteFlow 显示 → 选择模式 → 6 步流程走通 → 正文加载到编辑器
- Edge case 1：mode="fast" → Step 2B 被跳过，直接进入 Step 3
- Edge case 2：Step 3 审查结果显示六维评分条 + 问题列表
- Error case：取消创作 → 切回手动编辑模式，编辑器内容不变
