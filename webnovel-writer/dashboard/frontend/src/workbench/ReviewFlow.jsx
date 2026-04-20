import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel'
import RadarChart from './RadarChart'
import { startSkill } from '../api'

export default function ReviewFlow({ projectRoot, chapterStart, chapterEnd, onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)

  const handleStart = async () => {
    const result = await startSkill('review', {
      project_root: projectRoot,
      chapter_start: chapterStart,
      chapter_end: chapterEnd,
    })
    setSkillId(result.id)
  }

  if (!skillId) {
    return (
      <div className="review-start-screen">
        <h3>章节审查</h3>
        <p>审查范围：第{chapterStart}章 ~ 第{chapterEnd}章</p>
        <button className="btn-primary" onClick={handleStart}>
          开始审查
        </button>
      </div>
    )
  }

  return (
    <SkillFlowPanel
      skillId={skillId}
      stepRenderers={REVIEW_STEP_RENDERERS}
      onCompleted={onCompleted}
      onCancelled={onCancelled}
    />
  )
}

const REVIEW_STEP_RENDERERS = {
  step_1: AutoStepDisplay,
  step_2: AutoStepDisplay,
  step_3: ReviewProgressDisplay,
  step_4: ReviewReportConfirm,
  step_5: AutoStepDisplay,
  step_6: AutoStepDisplay,
  step_7: CriticalIssuesDecision,
  step_8: AutoStepDisplay,
}

function AutoStepDisplay({ stepState }) {
  const data = stepState.output_data || {}
  return (
    <div className="auto-step-display">
      <p>{data.instruction || '处理中...'}</p>
    </div>
  )
}

export function ReviewProgressDisplay({ stepState }) {
  const progress = stepState.progress || 0
  return (
    <div className="review-progress">
      <h4>六维并行审查</h4>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress * 100}%` }} />
      </div>
      <p>{progress < 1 ? `审查中... ${Math.round(progress * 100)}%` : '审查完成'}</p>
    </div>
  )
}

export function ReviewReportConfirm({ stepState, onSubmit }) {
  const report = stepState.output_data?.report || {}
  const overall = report.overall || {}

  return (
    <div className="review-report-confirm">
      <h4>审查报告</h4>

      <div className="overall-score">
        <span className="score-value">{overall.avg_score}/10</span>
        <span className={`verdict verdict-${overall.verdict}`}>{overall.verdict}</span>
      </div>

      <RadarChart dimensions={overall.dimension_scores || {}} size={280} />

      <div className="chapter-scores">
        <h5>各章评分</h5>
        {Object.entries(report.chapters || {}).map(([ch, data]) => (
          <div key={ch} className="chapter-score-row">
            <span>第{ch}章</span>
            <span className="ch-score">{data.score}</span>
            <span className="ch-issues">{data.issues_count} 个问题</span>
          </div>
        ))}
      </div>

      {report.suggestions?.length > 0 && (
        <div className="suggestions">
          <h5>改进建议</h5>
          <ul>
            {report.suggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {report.priority_fixes?.length > 0 && (
        <div className="priority-fixes">
          <h5>优先修复（{report.priority_fixes.length} 项）</h5>
          {report.priority_fixes.map((fix, i) => (
            <div key={i} className={`fix-item severity-${fix.severity}`}>
              <span className="severity-badge">{fix.severity}</span>
              <span>第{fix.chapter}章 — {fix.message}</span>
            </div>
          ))}
        </div>
      )}

      <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>
        确认报告
      </button>
    </div>
  )
}

export function CriticalIssuesDecision({ stepState, onSubmit }) {
  const { has_critical, auto_resolved, issues_with_options } = stepState.output_data || {}
  const [decisions, setDecisions] = useState([])

  if (!has_critical || auto_resolved) {
    return <p>无关键问题，自动通过。</p>
  }

  const handleDecision = (issueIndex, optionId) => {
    setDecisions(prev => {
      const next = [...prev]
      next[issueIndex] = {
        issue_index: issueIndex,
        option_id: optionId,
        issue: issues_with_options[issueIndex]?.issue,
      }
      return next
    })
  }

  return (
    <div className="critical-issues-decision">
      <h4>关键问题决策</h4>
      {(issues_with_options || []).map((item, i) => (
        <div key={i} className="critical-issue-card">
          <div className="issue-header">
            <span className="severity-badge">critical</span>
            <span>第{item.issue.chapter}章 — {item.issue.dimension}</span>
          </div>
          <p className="issue-message">{item.issue.message}</p>
          <div className="fix-options">
            {item.options.map(opt => (
              <label key={opt.id} className={`fix-option ${decisions[i]?.option_id === opt.id ? 'selected' : ''}`}>
                <input
                  type="radio"
                  name={`issue_${i}`}
                  checked={decisions[i]?.option_id === opt.id}
                  onChange={() => handleDecision(i, opt.id)}
                />
                <span className="option-label">{opt.label}</span>
                <span className="option-desc">{opt.description}</span>
              </label>
            ))}
          </div>
        </div>
      ))}
      <button
        className="btn-primary"
        onClick={() => onSubmit({ decisions })}
        disabled={decisions.filter(Boolean).length < (issues_with_options || []).length}
      >
        提交决策
      </button>
    </div>
  )
}
