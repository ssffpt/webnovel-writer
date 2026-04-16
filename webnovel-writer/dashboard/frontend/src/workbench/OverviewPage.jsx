import { buildOverviewModel, getNextSuggestion } from './data.js'

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
      <div className="workbench-panel" style={{ textAlign: 'center', padding: '40px 20px' }}>
        <div className="loading-spinner" />
        <p style={{ marginTop: 16, color: 'var(--text-sub)' }}>正在加载项目信息…</p>
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
      <div className="empty-state" style={{ padding: '80px 20px' }}>
        <div className="empty-icon" style={{ fontSize: 64 }}>📖</div>
        <h2 style={{ marginBottom: 12, fontSize: 24 }}>欢迎使用网文创作工作台</h2>
        <p style={{ color: 'var(--text-sub)', marginBottom: 24, fontSize: 15 }}>
          创建你的第一部小说，开始 AI 辅助创作之旅
        </p>
        <button type="button" className="workbench-primary-button" onClick={onCreateNew} style={{ fontSize: 16, padding: '14px 28px' }}>
          ＋ 创建新小说
        </button>
      </div>
    </section>
  )
}

// --- Incomplete State ---

function IncompleteState({ model, projectInfo, onContinueSetup }) {
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

      <div className="workbench-grid" style={{ marginTop: 20 }}>
        <div className="workbench-panel">
          <h3>项目概况</h3>
          <p>书名：{model.project?.title || '未命名项目'}</p>
          <p>题材：{model.project?.genre || '未设置'}</p>
          <p>当前章节：{model.progress?.current_chapter || '—'}</p>
        </div>
      </div>

      <div className="workbench-panel" style={{ marginTop: 16, borderColor: 'var(--accent-amber)' }}>
        <p style={{ fontWeight: 700, color: 'var(--accent-amber)' }}>
          项目设置尚未完成
        </p>
        <p style={{ marginTop: 8, color: 'var(--text-sub)', fontSize: 14 }}>
          完成项目设定后即可开始创作
        </p>
        <button type="button" className="workbench-primary-button" onClick={onContinueSetup || (() => {})} style={{ marginTop: 12 }}>
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
        <div className="next-step-card" style={{ marginTop: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h3 style={{ marginBottom: 4 }}>下一步</h3>
              <p style={{ color: 'var(--text-sub)', fontSize: 14 }}>{suggestion.text}</p>
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

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 20 }}>
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
                <li key={`activity-${i}`} style={{ fontSize: 13, padding: '4px 0' }}>
                  <span style={{ color: 'var(--text-mute)', marginRight: 8 }}>
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
  onContinueSetup,
  onNavigateToPage,
  onRunAction,
}) {
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
          onContinueSetup={onContinueSetup}
        />
      )

    case 'ready':
      return (
        <ReadyState
          model={model}
          projectInfo={projectInfo}
          recentActivities={recentActivities}
          onNavigateToPage={onNavigateToPage}
          onRunAction={onRunAction}
        />
      )

    default:
      return <EmptyState onCreateNew={onCreateNew} />
  }
}
