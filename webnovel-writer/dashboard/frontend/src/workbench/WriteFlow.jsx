import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel'
import { startSkill } from '../api'

// --- Step Renderers ---

export function ContextAgentDisplay({ stepState }) {
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

export function DraftConfirm({ stepState, onSubmit }) {
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

export function StyleAdaptConfirm({ stepState, onSubmit }) {
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

export function ReviewResultsDisplay({ stepState }) {
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

export function PolishConfirm({ stepState, onSubmit }) {
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

export function DataAgentDisplay({ stepState }) {
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

export function GitBackupDisplay({ stepState }) {
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

const WRITE_STEP_RENDERERS = {
  step_1: ContextAgentDisplay,
  step_2a: DraftConfirm,
  step_2b: StyleAdaptConfirm,
  step_3: ReviewResultsDisplay,
  step_4: PolishConfirm,
  step_5: DataAgentDisplay,
  step_6: GitBackupDisplay,
}

// --- WriteStartScreen ---

function WriteStartScreen({ chapterNum, mode, onModeChange, onStart, error }) {
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
      {error && <p className="error-text">{error}</p>}
      <button className="btn-primary" onClick={onStart}>
        开始创作
      </button>
    </div>
  )
}

// --- Main WriteFlow ---

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
  const [error, setError] = useState('')

  const handleStart = async () => {
    setError('')
    try {
      const result = await startSkill('write', {
        project_root: projectRoot,
        chapter_num: chapterNum,
        mode: mode,
      })
      setSkillId(result.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动创作失败')
    }
  }

  if (!skillId) {
    return (
      <WriteStartScreen
        chapterNum={chapterNum}
        mode={mode}
        onModeChange={setMode}
        onStart={handleStart}
        error={error}
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
