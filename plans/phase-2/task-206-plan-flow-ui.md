# Task 206: PlanFlow 前端组件 + OutlinePage 集成

## 目标

实现 PlanFlow 前端组件，嵌入 OutlinePage，用户可在大纲页启动卷级规划流程。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/PlanFlow.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/workbench/OutlinePage.jsx`（修改）
- `webnovel-writer/dashboard/frontend/src/api.js`（修改，如需新增 API 函数）

## 依赖

- task-205（后端 PlanSkillHandler 全部步骤完成）
- Phase 0 task-006（SkillFlowPanel 已存在）

## 前置知识

SkillFlowPanel 已实现通用的 Step 进度条 + 日志 + 表单/确认渲染。PlanFlow 基于它构建，但需要自定义每步的展示 UI。

api.js 中已有的 Skill API 函数（Phase 0 task-006）：

```javascript
export function startSkill(skillName, options = {}) { ... }
export function getSkillStatus(skillId) { ... }
export function submitSkillStep(skillId, stepId, data) { ... }
export function cancelSkill(skillId) { ... }
```

SkillFlowPanel 支持 `stepRenderers` prop（Phase 1 task-105 中已扩展）：

```jsx
<SkillFlowPanel
  skillId={skillId}
  stepRenderers={PLAN_STEP_RENDERERS}
  onCompleted={handleCompleted}
  onCancelled={handleCancelled}
/>
```

## 规格

### PlanFlow 组件

```jsx
import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel'
import { startSkill } from '../api'

/**
 * 卷规划流程面板，嵌入 OutlinePage。
 *
 * Props:
 *   projectRoot: string — 项目根目录
 *   onCompleted(volumeName: string) — 规划完成回调
 *   onCancelled() — 取消回调
 */
export default function PlanFlow({ projectRoot, onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)
  const [volumeConfig, setVolumeConfig] = useState({
    volume_name: '',
    chapter_start: '',
    chapter_end: '',
  })

  const handleStart = async () => {
    const result = await startSkill('plan', {
      project_root: projectRoot,
    })
    setSkillId(result.id)
  }

  if (!skillId) {
    return <PlanStartScreen onStart={handleStart} />
  }

  return (
    <SkillFlowPanel
      skillId={skillId}
      stepRenderers={PLAN_STEP_RENDERERS}
      onCompleted={() => onCompleted(volumeConfig.volume_name)}
      onCancelled={onCancelled}
    />
  )
}
```

### PlanStartScreen

```jsx
function PlanStartScreen({ onStart }) {
  return (
    <div className="plan-start-screen">
      <h3>卷级规划</h3>
      <p>启动 8 步卷级规划流程，生成节拍表、时间线、卷骨架和章节大纲。</p>
      <button className="btn-primary" onClick={onStart}>
        开始规划
      </button>
    </div>
  )
}
```

### stepRenderers — 每步的自定义渲染

```javascript
const PLAN_STEP_RENDERERS = {
  step_1: AutoStepDisplay,          // 加载项目数据（auto，显示加载结果）
  step_2: AutoStepDisplay,          // 构建设定基线（auto，显示结果）
  step_3: VolumeSelectionForm,      // 选择卷（form）
  step_4: BeatSheetConfirm,         // 节拍表确认（confirm）
  step_4_5: TimelineConfirm,        // 时间线确认（confirm）
  step_5: SkeletonConfirm,          // 卷骨架确认（confirm）
  step_6: ChapterOutlineProgress,   // 章节大纲生成进度（auto + 进度条）
  step_7: WritebackDisplay,         // 回写设定集（auto，可能有 BLOCKER）
  step_8: ValidationResults,        // 验证结果展示（auto）
}
```

### Step 3 — VolumeSelectionForm

```jsx
function VolumeSelectionForm({ stepState, onSubmit }) {
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

  return (
    <form onSubmit={e => { e.preventDefault(); onSubmit(formData) }}>
      <div className="form-group">
        <label>卷名 <span className="required">*</span></label>
        <input
          type="text"
          value={formData.volume_name}
          onChange={e => handleChange('volume_name', e.target.value)}
          placeholder="如：第一卷·初入江湖"
        />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>起始章 <span className="required">*</span></label>
          <input
            type="number"
            value={formData.chapter_start}
            onChange={e => handleChange('chapter_start', e.target.value)}
          />
        </div>
        <div className="form-group">
          <label>结束章 <span className="required">*</span></label>
          <input
            type="number"
            value={formData.chapter_end}
            onChange={e => handleChange('chapter_end', e.target.value)}
          />
        </div>
      </div>
      <div className="form-group">
        <label>本卷主题</label>
        <textarea
          value={formData.volume_theme}
          onChange={e => handleChange('volume_theme', e.target.value)}
          placeholder="本卷的核心主题或目标"
        />
      </div>
      <div className="form-group">
        <label>特殊需求</label>
        <textarea
          value={formData.special_requirements}
          onChange={e => handleChange('special_requirements', e.target.value)}
          placeholder="对本卷的特殊要求（可选）"
        />
      </div>
      <button type="submit" className="btn-primary">确认</button>
    </form>
  )
}
```

### Step 4 — BeatSheetConfirm

```jsx
function BeatSheetConfirm({ stepState, onSubmit }) {
  const beats = stepState.output_data?.beats || []
  const [feedback, setFeedback] = useState('')

  return (
    <div className="beat-sheet-confirm">
      <h3>卷节拍表</h3>
      <div className="beat-list">
        {beats.map(beat => (
          <div key={beat.chapter} className={`beat-card ${beat.is_climax ? 'climax' : ''}`}>
            <div className="beat-chapter">第{beat.chapter}章</div>
            <div className="beat-act">{beat.act}</div>
            <div className="beat-event">{beat.event}</div>
            <div className="beat-emotion">{beat.emotion_curve}</div>
            {beat.is_climax && <span className="climax-badge">高潮</span>}
          </div>
        ))}
      </div>
      <div className="confirm-actions">
        <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>
          确认节拍表
        </button>
        <div className="feedback-input">
          <textarea
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            placeholder="修改意见（可选）"
          />
          <button
            className="btn-secondary"
            onClick={() => onSubmit({ confirmed: false, feedback })}
            disabled={!feedback}
          >
            提交修改意见
          </button>
        </div>
      </div>
    </div>
  )
}
```

### Step 4.5 — TimelineConfirm

```jsx
function TimelineConfirm({ stepState, onSubmit }) {
  const timeline = stepState.output_data?.timeline || []
  const [feedback, setFeedback] = useState('')

  return (
    <div className="timeline-confirm">
      <h3>卷时间线</h3>
      <div className="timeline-list">
        {timeline.map((event, i) => (
          <div key={i} className="timeline-event">
            <div className="timeline-day">Day {event.day}</div>
            <div className="timeline-chapter">第{event.chapter}章</div>
            <div className="timeline-location">{event.location}</div>
            <div className="timeline-characters">{event.characters.join('、')}</div>
            <div className="timeline-desc">{event.event}</div>
            <span className="strand-tag">{event.strand}</span>
          </div>
        ))}
      </div>
      <div className="confirm-actions">
        <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>
          确认时间线
        </button>
        <div className="feedback-input">
          <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="修改意见" />
          <button className="btn-secondary" onClick={() => onSubmit({ confirmed: false, feedback })} disabled={!feedback}>
            提交修改意见
          </button>
        </div>
      </div>
    </div>
  )
}
```

### Step 6 — ChapterOutlineProgress

```jsx
function ChapterOutlineProgress({ stepState }) {
  const progress = stepState.progress || 0
  const outlines = stepState.output_data?.chapter_outlines || []
  const total = stepState.output_data?.total_generated || 0

  return (
    <div className="chapter-outline-progress">
      <h3>生成章节大纲</h3>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress * 100}%` }} />
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
            <div key={o.chapter} className="outline-card">
              <strong>{o.title}</strong>
              <p>{o.summary}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### Step 7 — WritebackDisplay（含 BLOCKER 处理）

```jsx
function WritebackDisplay({ stepState, onSubmit }) {
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
        className="btn-primary"
        onClick={() => onSubmit({ blocker_decisions: decisions })}
        disabled={decisions.filter(Boolean).length < blockers.length}
      >
        提交决策
      </button>
    </div>
  )
}
```

### Step 8 — ValidationResults

```jsx
function ValidationResults({ stepState }) {
  const results = stepState.output_data?.validation_results || []
  const allPassed = stepState.output_data?.all_passed

  return (
    <div className="validation-results">
      <h3>验证结果</h3>
      <div className="check-list">
        {results.map((r, i) => (
          <div key={i} className={`check-item ${r.passed ? 'passed' : 'failed'}`}>
            <span className="check-icon">{r.passed ? '✓' : '✗'}</span>
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
```

### OutlinePage 集成

修改 `OutlinePage.jsx`，将"生成大纲"按钮替换为启动 PlanFlow：

```jsx
// OutlinePage.jsx 中新增
import PlanFlow from './PlanFlow'

// 在组件内部
const [showPlanFlow, setShowPlanFlow] = useState(false)

// 原来的"生成第N卷大纲"按钮改为：
<button onClick={() => setShowPlanFlow(true)}>
  生成卷大纲
</button>

// 当 showPlanFlow 为 true 时，编辑区域替换为 PlanFlow：
{showPlanFlow ? (
  <PlanFlow
    projectRoot={projectRoot}
    onCompleted={(volumeName) => {
      setShowPlanFlow(false)
      // 刷新文件列表，加载新生成的大纲
      refreshFileList()
    }}
    onCancelled={() => setShowPlanFlow(false)}
  />
) : (
  // 原有的 markdown 编辑器
  <MarkdownEditor ... />
)}
```

### AutoStepDisplay（通用 auto 步骤展示）

```jsx
function AutoStepDisplay({ stepState }) {
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
```

### SkeletonConfirm（Step 5 卷骨架确认）

```jsx
function SkeletonConfirm({ stepState, onSubmit }) {
  const skeleton = stepState.output_data?.skeleton || {}
  const [feedback, setFeedback] = useState('')

  return (
    <div className="skeleton-confirm">
      <h3>卷骨架</h3>

      <section>
        <h4>Strand 规划</h4>
        {(skeleton.strands || []).map(s => (
          <div key={s.name} className="strand-card">
            <strong>{s.name}</strong>：{s.description}（{s.chapters?.length || 0} 章）
          </div>
        ))}
      </section>

      <section>
        <h4>爽点分布</h4>
        {(skeleton.hook_points || []).map((hp, i) => (
          <div key={i} className="hook-card">
            第{hp.chapter}章 — <span className="hook-type">{hp.type}</span>：{hp.description}
          </div>
        ))}
      </section>

      <section>
        <h4>伏笔布局</h4>
        {(skeleton.foreshadowing || []).map(f => (
          <div key={f.id} className="foreshadow-card">
            {f.description}（第{f.plant_chapter}章埋设 → 第{f.reveal_chapter}章揭示）
          </div>
        ))}
      </section>

      <div className="confirm-actions">
        <button className="btn-primary" onClick={() => onSubmit({ confirmed: true })}>
          确认卷骨架
        </button>
        <div className="feedback-input">
          <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="修改意见" />
          <button className="btn-secondary" onClick={() => onSubmit({ confirmed: false, feedback })} disabled={!feedback}>
            提交修改意见
          </button>
        </div>
      </div>
    </div>
  )
}
```

## TDD 验收

- Happy path：OutlinePage 点击"生成卷大纲" → PlanFlow 显示 → 8 步流程走通 → 完成后切回编辑器
- Edge case 1：Step 6 进度条从 0% 递增到 100%，显示最近生成的章节预览
- Edge case 2：Step 7 有 BLOCKER → 显示冲突卡片 → 用户决策后提交
- Error case：Step 8 验证失败 → 显示失败项 + 建议修复方案
