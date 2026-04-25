import { buildOverviewModel, getNextSuggestion } from './data.js'
import InitWizard from './InitWizard.jsx'

// --- Step Progress Bar ---

function StepProgressBar({ steps }) {
  return (
    <div className="step-progress-bar">
      {steps.map((step, i) => (
        <div
          key={step.label}
          className={`step-progress-item ${step.status === 'completed' ? 'completed' : ''} ${step.status === 'active' ? 'active' : ''}`}
        >
          <span className="step-progress-marker">
            {step.status === 'completed' ? '✓' : step.status === 'active' ? '●' : '○'}
          </span>
          <span className="step-progress-label">{step.label}</span>
          {i < steps.length - 1 && <span className="step-progress-connector" />}
        </div>
      ))}
    </div>
  )
}

// --- Loading State ---

function LoadingState() {
  return (
    <section className="workbench-page">
      <div className="workbench-panel overview-loading-panel">
        <div className="loading-spinner" />
        <p className="overview-loading-text">正在加载项目信息…</p>
      </div>
    </section>
  )
}

// --- Error State ---

function ErrorState({ error, onRetry }) {
  return (
    <section className="workbench-page">
      <div className="workbench-panel">
        <h2>总览</h2>
        <p className="error-text">{error}</p>
        <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
      </div>
    </section>
  )
}

// --- Empty State (no project) ---

function EmptyState({ onCreateNew }) {
  return (
    <section className="workbench-page">
      <div className="empty-state overview-empty-state">
        <div className="empty-icon overview-empty-icon">📖</div>
        <h2 className="overview-empty-title">欢迎使用网文创作工作台</h2>
        <p className="overview-empty-desc">
          创建你的第一部小说，开始 AI 辅助创作之旅
        </p>
        <button type="button" className="workbench-primary-button overview-empty-button" onClick={onCreateNew}>
          ＋ 创建新小说
        </button>
      </div>
    </section>
  )
}

// --- Incomplete State ---

function IncompleteState({ model, projectInfo, onCreateNew }) {
  const steps = [
    { label: '起步', status: 'active' },
    { label: '写作中', status: 'pending' },
    { label: '审查', status: 'pending' },
  ]

  return (
    <section className="workbench-page">
      <div className="page-header">
        <h2>总览</h2>
      </div>

      <StepProgressBar steps={steps} />

      <div className="workbench-grid overview-grid-spaced">
        <div className="workbench-panel">
          <h3>项目概况</h3>
          <p>书名：{model.project?.title || '未命名项目'}</p>
          <p>题材：{model.project?.genre || '未设置'}</p>
          <p>当前章节：{model.progress?.current_chapter || '—'}</p>
        </div>
      </div>

      <div className="workbench-panel overview-incomplete-panel">
        <p className="overview-incomplete-title">
          项目设置尚未完成
        </p>
        <p className="overview-incomplete-desc">
          完成项目设定后即可开始创作
        </p>
        <button type="button" className="workbench-primary-button overview-incomplete-button" onClick={onCreateNew || (() => {})}>
          继续设置
        </button>
      </div>
    </section>
  )
}

// --- Ready State ---

function ReadyState({ model, projectInfo, recentActivities, onNavigateToPage, onRunAction }) {
  const suggestion = getNextSuggestion(model)

  const steps = [
    { label: '起步', status: 'completed' },
    { label: '写作中', status: (model.progress?.current_chapter || 0) > 0 ? 'active' : 'pending' },
    { label: '审查', status: 'pending' },
  ]

  return (
    <section className="workbench-page">
      <div className="page-header">
        <h2>总览</h2>
      </div>

      <StepProgressBar steps={steps} />

      {suggestion && (
        <div className="next-step-card overview-next-step-card">
          <div className="overview-next-step-header">
            <div>
              <h3 className="overview-next-step-title">下一步</h3>
              <p className="overview-next-step-text">{suggestion.text}</p>
            </div>
            <button
              type="button"
              className="workbench-primary-button"
              onClick={() => {
                if (onRunAction) {
                  onRunAction({ type: suggestion.action, label: suggestion.text, ...suggestion.params })
                }
                if (onNavigateToPage) {
                  onNavigateToPage('chapters')
                }
              }}
            >
              {suggestion.text}
            </button>
          </div>
        </div>
      )}

      <div className="overview-two-col-grid">
        <div className="workbench-panel">
          <h3>项目概况</h3>
          <p>书名：{model.project?.title || '未命名项目'}</p>
          <p>题材：{model.project?.genre || '未设置'}</p>
          <p>当前章节：{model.progress?.current_chapter || '—'}</p>
          {model.progress?.total_words != null && (
            <p>总字数：{model.progress.total_words.toLocaleString()}</p>
          )}
        </div>

        <div className="workbench-panel">
          <h3>最近动态</h3>
          {(!recentActivities || recentActivities.length === 0) ? (
            <p className="empty-text">暂无最近动态。</p>
          ) : (
            <ul className="workbench-meta-list">
              {recentActivities.slice(0, 5).map((activity, i) => (
                <li key={`activity-${i}`} className="overview-activity-item">
                  <span className="overview-activity-time">
                    {activity.time || activity.timestamp || ''}
                  </span>
                  <span>{activity.message || activity.description || JSON.stringify(activity)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  )
}

// --- Main Component ---

export default function OverviewPage({
  summary,
  loading,
  loadError,
  onRetry,
  projectStatus,
  projectInfo,
  recentActivities,
  onCreateNew,
  showWizard,
  onWizardClosed,
  onWizardCompleted,
  onNavigateToPage,
  onRunAction,
}) {
  if (showWizard) {
    return (
      <section className="workbench-page">
        <InitWizard onCompleted={onWizardCompleted} onCancelled={onWizardClosed} />
      </section>
    )
  }

  if (loading || projectStatus === 'loading') {
    return <LoadingState />
  }

  if (loadError) {
    return <ErrorState error={loadError} onRetry={onRetry} />
  }

  const model = buildOverviewModel(summary)

  switch (projectStatus) {
    case 'no-project':
      return <EmptyState onCreateNew={onCreateNew} />

    case 'incomplete':
      return (
        <IncompleteState
          model={model}
          projectInfo={projectInfo}
          onCreateNew={onCreateNew}
        />
      )

    case 'ready':
      return (
        <section className="workbench-page">
          <div className="page-header">
            <h2>总览</h2>
          </div>
          <ReadyState
            model={model}
            projectInfo={projectInfo}
            recentActivities={recentActivities}
            onNavigateToPage={onNavigateToPage}
            onRunAction={onRunAction}
          />
        </section>
      )

    default:
      return <EmptyState onCreateNew={onCreateNew} />
  }
}
