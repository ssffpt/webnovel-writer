# Task 405: ReviewFlow 前端组件 + 六维雷达图

## 目标

实现 ReviewFlow 前端组件和 RadarChart 六维雷达图组件，嵌入 ChapterPage 侧面板。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/ReviewFlow.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/workbench/RadarChart.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/workbench/ChapterPage.jsx`（修改，新增审查按钮）

## 依赖

- task-404（后端 ReviewSkillHandler 全部步骤完成）
- Phase 0 task-006（SkillFlowPanel 已存在）

## 前置知识

api.js 中已有的 Skill API 函数：

```javascript
export function startSkill(skillName, options = {}) { ... }
export function getSkillStatus(skillId) { ... }
export function submitSkillStep(skillId, stepId, data) { ... }
export function cancelSkill(skillId) { ... }
```

## 规格

### RadarChart 组件

```jsx
/**
 * 六维雷达图。纯 Canvas/SVG 实现，无外部依赖。
 *
 * Props:
 *   dimensions: { [name: string]: number } — 维度名→分数(0-10)
 *   size: number — 图表尺寸（默认 250）
 */
export default function RadarChart({ dimensions, size = 250 }) {
  const entries = Object.entries(dimensions || {})
  const count = entries.length
  if (count < 3) return null

  const center = size / 2
  const radius = size / 2 - 30
  const angleStep = (2 * Math.PI) / count

  // 计算各顶点坐标
  const getPoint = (index, value) => {
    const angle = angleStep * index - Math.PI / 2
    const r = (value / 10) * radius
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    }
  }

  // 网格线（5 层）
  const gridLevels = [2, 4, 6, 8, 10]
  const gridPaths = gridLevels.map(level => {
    const points = entries.map((_, i) => getPoint(i, level))
    return points.map(p => `${p.x},${p.y}`).join(' ')
  })

  // 数据多边形
  const dataPoints = entries.map(([_, score], i) => getPoint(i, score))
  const dataPath = dataPoints.map(p => `${p.x},${p.y}`).join(' ')

  // 轴线 + 标签
  const axes = entries.map(([name, score], i) => {
    const outerPoint = getPoint(i, 10)
    const labelPoint = getPoint(i, 12)
    return { name, score, outerPoint, labelPoint }
  })

  return (
    <svg width={size} height={size} className="radar-chart">
      {/* 网格 */}
      {gridPaths.map((points, i) => (
        <polygon
          key={i}
          points={points}
          fill="none"
          stroke="#e0e0e0"
          strokeWidth="1"
        />
      ))}

      {/* 轴线 */}
      {axes.map((axis, i) => (
        <line
          key={i}
          x1={center} y1={center}
          x2={axis.outerPoint.x} y2={axis.outerPoint.y}
          stroke="#e0e0e0"
          strokeWidth="1"
        />
      ))}

      {/* 数据多边形 */}
      <polygon
        points={dataPath}
        fill="rgba(59, 130, 246, 0.2)"
        stroke="#3b82f6"
        strokeWidth="2"
      />

      {/* 数据点 */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4" fill="#3b82f6" />
      ))}

      {/* 标签 */}
      {axes.map((axis, i) => (
        <text
          key={i}
          x={axis.labelPoint.x}
          y={axis.labelPoint.y}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize="12"
          fill="#666"
        >
          {axis.name} ({axis.score})
        </text>
      ))}
    </svg>
  )
}
```

### ReviewFlow 组件

```jsx
import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel'
import RadarChart from './RadarChart'
import { startSkill } from '../api'

/**
 * 审查流程面板，嵌入 ChapterPage 侧面板。
 *
 * Props:
 *   projectRoot: string
 *   chapterStart: number
 *   chapterEnd: number
 *   onCompleted() — 审查完成回调
 *   onCancelled() — 取消回调
 */
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
```

### stepRenderers

```javascript
const REVIEW_STEP_RENDERERS = {
  step_1: AutoStepDisplay,          // 加载参考（auto）
  step_2: AutoStepDisplay,          // 加载项目状态（auto）
  step_3: ReviewProgressDisplay,    // 并行审查（auto + 进度）
  step_4: ReviewReportConfirm,      // 审查报告（confirm + 雷达图）
  step_5: AutoStepDisplay,          // 保存指标（auto）
  step_6: AutoStepDisplay,          // 写回记录（auto）
  step_7: CriticalIssuesDecision,   // 关键问题决策（confirm）
  step_8: AutoStepDisplay,          // 收尾（auto）
}
```

### Step 3 — ReviewProgressDisplay

```jsx
function ReviewProgressDisplay({ stepState }) {
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
```

### Step 4 — ReviewReportConfirm（含雷达图）

```jsx
function ReviewReportConfirm({ stepState, onSubmit }) {
  const report = stepState.output_data?.report || {}
  const overall = report.overall || {}

  return (
    <div className="review-report-confirm">
      <h4>审查报告</h4>

      {/* 总评 */}
      <div className="overall-score">
        <span className="score-value">{overall.avg_score}/10</span>
        <span className={`verdict verdict-${overall.verdict}`}>{overall.verdict}</span>
      </div>

      {/* 六维雷达图 */}
      <RadarChart dimensions={overall.dimension_scores || {}} size={280} />

      {/* 各章评分 */}
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

      {/* 改进建议 */}
      {report.suggestions?.length > 0 && (
        <div className="suggestions">
          <h5>改进建议</h5>
          <ul>
            {report.suggestions.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      )}

      {/* 优先修复 */}
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
```

### Step 7 — CriticalIssuesDecision

```jsx
function CriticalIssuesDecision({ stepState, onSubmit }) {
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
```

### AutoStepDisplay（通用）

```jsx
function AutoStepDisplay({ stepState }) {
  const data = stepState.output_data || {}
  return (
    <div className="auto-step-display">
      <p>{data.instruction || '处理中...'}</p>
    </div>
  )
}
```

### ChapterPage 集成

修改 `ChapterPage.jsx`，新增审查按钮和侧面板：

```jsx
import ReviewFlow from './ReviewFlow'

// 在组件内部
const [showReview, setShowReview] = useState(false)

// 编辑器顶部新增审查按钮
<button
  className="btn-review"
  onClick={() => setShowReview(true)}
>
  审查本章
</button>

// 侧面板
{showReview && (
  <div className="review-side-panel">
    <ReviewFlow
      projectRoot={projectRoot}
      chapterStart={currentChapterNum}
      chapterEnd={currentChapterNum}
      onCompleted={() => setShowReview(false)}
      onCancelled={() => setShowReview(false)}
    />
  </div>
)}
```

## TDD 验收

- Happy path：点击"审查本章" → ReviewFlow 侧面板显示 → 8 步走通 → 雷达图正确渲染 6 维评分
- Edge case 1：无 critical 问题 → Step 7 自动跳过 → 直接进入 Step 8
- Edge case 2：RadarChart 传入 3 个维度 → 正确渲染三角形
- Error case：取消审查 → 侧面板关闭，不影响编辑器
