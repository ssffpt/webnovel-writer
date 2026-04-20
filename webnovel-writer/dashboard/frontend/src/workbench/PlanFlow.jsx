import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel.jsx'
import { startSkill } from '../api.js'

// --- PlanStartScreen ---

function PlanStartScreen({ onStart }) {
  return (
    <div className="plan-start-screen workbench-panel">
      <div className="plan-start-content">
        <h3>卷级规划</h3>
        <p>启动 8 步卷级规划流程，生成节拍表、时间线、卷骨架和章节大纲。</p>
        <button className="workbench-primary-button" onClick={onStart}>
          开始规划
        </button>
      </div>
    </div>
  )
}

// --- AutoStepDisplay (Step 1-2) ---

export function AutoStepDisplay({ stepState }) {
  const data = stepState.output_data || {}
  return (
    <div className="auto-step-display">
      <p>{data.instruction || '处理中...'}</p>
      {data.loaded !== undefined && <p>项目数据已加载，共 {data.volumes_count || 0} 卷</p>}
      {data.baseline_ready && <p>设定基线构建完成</p>}
      {data.missing_created?.length > 0 && (
        <p>已创建缺失设定模板：{data.missing_created.join('、')}</p>
      )}
    </div>
  )
}

// --- VolumeSelectionForm (Step 3) ---

export function VolumeSelectionForm({ stepState, onSubmit }) {
  const [formData, setFormData] = useState({
    volume_name: '',
    chapter_start: '',
    chapter_end: '',
    volume_theme: '',
    special_requirements: '',
  })

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    onSubmit(formData)
  }

  return (
    <form className="volume-selection-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label>卷名 <span className="required">*</span></label>
        <input
          type="text"
          value={formData.volume_name}
          onChange={e => handleChange('volume_name', e.target.value)}
          placeholder="如：第一卷·初入江湖"
          required
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>起始章 <span className="required">*</span></label>
          <input
            type="number"
            value={formData.chapter_start}
            onChange={e => handleChange('chapter_start', e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>结束章 <span className="required">*</span></label>
          <input
            type="number"
            value={formData.chapter_end}
            onChange={e => handleChange('chapter_end', e.target.value)}
            required
          />
        </div>
      </div>
      <div className="form-group">
        <label>本卷主题</label>
        <textarea
          value={formData.volume_theme}
          onChange={e => handleChange('volume_theme', e.target.value)}
          placeholder="本卷的核心主题或目标"
          rows={3}
        />
      </div>
      <div className="form-group">
        <label>特殊需求</label>
        <textarea
          value={formData.special_requirements}
          onChange={e => handleChange('special_requirements', e.target.value)}
          placeholder="对本卷的特殊要求（可选）"
          rows={2}
        />
      </div>
      <button type="submit" className="workbench-primary-button">确认</button>
    </form>
  )
}

// --- BeatSheetConfirm / BeatTableViewer (Step 4) ---

export function BeatSheetConfirm({ stepState, onSubmit }) {
  return <BeatTableViewer stepState={stepState} onSubmit={onSubmit} />
}

export function BeatTableViewer({ stepState, onSubmit }) {
  const beats = stepState.output_data?.beats || []
  const [feedback, setFeedback] = useState('')

  const handleConfirm = () => {
    onSubmit({ confirmed: true })
  }

  const handleSubmitFeedback = () => {
    if (feedback.trim()) {
      onSubmit({ confirmed: false, feedback })
    }
  }

  return (
    <div className="beat-table-viewer">
      <h3>卷节拍表</h3>
      {beats.length > 0 ? (
        <table className="beat-table">
          <thead>
            <tr>
              <th>章</th>
              <th>节拍</th>
              <th>事件</th>
              <th>情感曲线</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {beats.map((beat, i) => (
              <tr key={i}>
                <td>第{beat.chapter}章</td>
                <td>{beat.act}</td>
                <td>{beat.event}</td>
                <td>{beat.emotion_curve}</td>
                <td>{beat.is_climax && <span className="climax-badge">高潮</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-text">暂无节拍数据</p>
      )}
      <div className="confirm-actions">
        <button className="workbench-primary-button" onClick={handleConfirm}>
          确认节拍表
        </button>
        <div className="feedback-input">
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="修改意见（可选）"
            rows={2}
          />
          <button
            className="workbench-nav-button"
            onClick={handleSubmitFeedback}
            disabled={!feedback.trim()}
          >
            提交修改意见
          </button>
        </div>
      </div>
    </div>
  )
}

// --- TimelineConfirm (Step 4.5) ---

export function TimelineConfirm({ stepState, onSubmit }) {
  const timeline = stepState.output_data?.timeline || []
  const [feedback, setFeedback] = useState('')

  const handleConfirm = () => {
    onSubmit({ confirmed: true })
  }

  const handleSubmitFeedback = () => {
    if (feedback.trim()) {
      onSubmit({ confirmed: false, feedback })
    }
  }

  return (
    <div className="timeline-confirm">
      <h3>卷时间线</h3>
      {timeline.length > 0 ? (
        <div className="timeline-list">
          {timeline.map((event, i) => (
            <div key={i} className="timeline-event">
              <div className="timeline-day">Day {event.day}</div>
              <div className="timeline-chapter">第{event.chapter}章</div>
              <div className="timeline-location">{event.location}</div>
              <div className="timeline-characters">
                {Array.isArray(event.characters) ? event.characters.join('、') : event.characters}
              </div>
              <div className="timeline-desc">{event.event}</div>
              <span className="strand-tag">{event.strand}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="empty-text">暂无时间线数据</p>
      )}
      <div className="confirm-actions">
        <button className="workbench-primary-button" onClick={handleConfirm}>
          确认时间线
        </button>
        <div className="feedback-input">
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="修改意见"
            rows={2}
          />
          <button
            className="workbench-nav-button"
            onClick={handleSubmitFeedback}
            disabled={!feedback.trim()}
          >
            提交修改意见
          </button>
        </div>
      </div>
    </div>
  )
}

// --- SkeletonConfirm (Step 5) ---

export function SkeletonConfirm({ stepState, onSubmit }) {
  const skeleton = stepState.output_data?.skeleton || {}
  const [feedback, setFeedback] = useState('')

  const handleConfirm = () => {
    onSubmit({ confirmed: true })
  }

  const handleSubmitFeedback = () => {
    if (feedback.trim()) {
      onSubmit({ confirmed: false, feedback })
    }
  }

  return (
    <div className="skeleton-confirm">
      <h3>卷骨架</h3>

      <section>
        <h4>Strand 规划</h4>
        {skeleton.strands?.length > 0 ? (
          skeleton.strands.map((s, i) => (
            <div key={i} className="strand-card">
              <strong>{s.name}</strong>：{s.description}（{s.chapters?.length || 0} 章）
            </div>
          ))
        ) : (
          <p className="empty-text">暂无 Strand 规划</p>
        )}
      </section>

      <section>
        <h4>爽点分布</h4>
        {skeleton.hook_points?.length > 0 ? (
          skeleton.hook_points.map((hp, i) => (
            <div key={i} className="hook-card">
              第{hp.chapter}章 — <span className="hook-type">{hp.type}</span>：{hp.description}
            </div>
          ))
        ) : (
          <p className="empty-text">暂无爽点分布</p>
        )}
      </section>

      <section>
        <h4>伏笔布局</h4>
        {skeleton.foreshadowing?.length > 0 ? (
          skeleton.foreshadowing.map((f, i) => (
            <div key={i} className="foreshadow-card">
              {f.description}（第{f.plant_chapter}章埋设 → 第{f.reveal_chapter}章揭示）
            </div>
          ))
        ) : (
          <p className="empty-text">暂无伏笔布局</p>
        )}
      </section>

      <div className="confirm-actions">
        <button className="workbench-primary-button" onClick={handleConfirm}>
          确认卷骨架
        </button>
        <div className="feedback-input">
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="修改意见"
            rows={2}
          />
          <button
            className="workbench-nav-button"
            onClick={handleSubmitFeedback}
            disabled={!feedback.trim()}
          >
            提交修改意见
          </button>
        </div>
      </div>
    </div>
  )
}

// --- ChapterOutlineProgress / ChapterOutlinesViewer (Step 6) ---

export function ChapterOutlineProgress({ stepState }) {
  return <ChapterOutlinesViewer stepState={stepState} onSubmit={() => {}} />
}

export function ChapterOutlinesViewer({ stepState, onSubmit }) {
  const progress = stepState.progress || 0
  const outlines = stepState.output_data?.chapter_outlines || []
  const total = stepState.output_data?.total_generated || 0

  return (
    <div className="chapter-outline-progress">
      <h3>章节大纲</h3>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${Math.round(progress * 100)}%` }} />
      </div>
      <p className="progress-text">
        {progress < 1
          ? `正在生成... ${Math.round(progress * 100)}%`
          : `已生成 ${total} 章大纲`}
      </p>
      {outlines.length > 0 && (
        <div className="outline-preview">
          <h4>已生成的章节：</h4>
          {outlines.slice(-3).map(o => (
            <div key={o.chapter || o.title} className="outline-card">
              <strong>{o.title}</strong>
              <p>{o.summary}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// --- WritebackDisplay (Step 7) ---

export function WritebackDisplay({ stepState, onSubmit }) {
  const { additions_count, blockers, has_blockers } = stepState.output_data || {}
  const [decisions, setDecisions] = useState([])

  if (!has_blockers) {
    return (
      <div className="writeback-display">
        <p>设定集回写完成，新增 {additions_count || 0} 条设定。</p>
      </div>
    )
  }

  const handleDecision = (index, action) => {
    setDecisions(prev => {
      const next = [...prev]
      next[index] = { blocker_index: index, action }
      return next
    })
  }

  const canSubmit = decisions.filter(Boolean).length >= blockers.length

  return (
    <div className="writeback-display">
      <p>新增 {additions_count || 0} 条设定。</p>
      <h4>检测到 {blockers.length} 个设定冲突：</h4>
      {blockers.map((b, i) => (
        <div key={i} className="blocker-card">
          <p className="blocker-fact">{b.fact}</p>
          <p className="blocker-conflict">冲突：{b.conflict}</p>
          <p className="blocker-suggestion">建议：{b.suggestion}</p>
          <div className="blocker-actions">
            <button onClick={() => handleDecision(i, 'accept')}>接受新设定</button>
            <button onClick={() => handleDecision(i, 'reject')}>保留旧设定</button>
          </div>
        </div>
      ))}
      <button
        className="workbench-primary-button"
        onClick={() => onSubmit({ blocker_decisions: decisions })}
        disabled={!canSubmit}
      >
        提交决策
      </button>
    </div>
  )
}

// --- ValidationResults (Step 8) ---

export function ValidationResults({ stepState }) {
  const results = stepState.output_data?.validation_results || []
  const allPassed = stepState.output_data?.all_passed

  return (
    <div className="validation-results">
      <h3>验证结果</h3>
      <div className="check-list">
        {results.map((r, i) => (
          <div key={i} className={`check-item ${r.passed ? 'passed' : 'failed'}`}>
            <span className="check-icon">{r.passed ? '\u2713' : '\u2717'}</span>
            <span className="check-name">{r.name}</span>
            <span className="check-detail">{r.detail}</span>
            {!r.passed && r.suggestion && (
              <p className="check-suggestion">{r.suggestion}</p>
            )}
          </div>
        ))}
      </div>
      {allPassed && <p className="success-message">全部验证通过，文件已保存。</p>}
    </div>
  )
}

// --- stepRenderers mapping ---

const PLAN_STEP_RENDERERS = {
  step_1: AutoStepDisplay,
  step_2: AutoStepDisplay,
  step_3: VolumeSelectionForm,
  step_4: BeatSheetConfirm,
  step_4_5: TimelineConfirm,
  step_5: SkeletonConfirm,
  step_6: ChapterOutlineProgress,
  step_7: WritebackDisplay,
  step_8: ValidationResults,
}

// --- Main PlanFlow Component ---

/**
 * 卷规划流程面板，嵌入 OutlinePage。
 *
 * Props:
 *   projectRoot: string — 项目根目录
 *   onCompleted(volumeName?: string) — 规划完成回调
 *   onCancelled() — 取消回调
 */
export default function PlanFlow({ projectRoot, onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)

  const handleStart = async () => {
    setError(null)
    setStarting(true)
    try {
      const result = await startSkill('plan', {
        context: {
          project_root: projectRoot,
        },
      })
      setSkillId(result.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : '启动规划失败')
    } finally {
      setStarting(false)
    }
  }

  if (!skillId) {
    return (
      <>
        {error && (
          <div className="plan-start-screen workbench-panel">
            <div className="plan-start-content">
              <h3>卷级规划</h3>
              <p className="error-text">{error}</p>
              <button className="workbench-primary-button" onClick={handleStart}>
                重试
              </button>
            </div>
          </div>
        )}
        {!error && <PlanStartScreen onStart={handleStart} />}
      </>
    )
  }

  return (
    <SkillFlowPanel
      skillId={skillId}
      stepRenderers={PLAN_STEP_RENDERERS}
      onCompleted={() => onCompleted?.()}
      onCancelled={onCancelled}
    />
  )
}