import { buildOverviewModel } from './data.js'

export default function OverviewPage({ summary, loading, loadError, onRetry }) {
  const model = buildOverviewModel(summary)

  if (loading) {
    return <section className="workbench-page"><div className="workbench-panel">正在加载总览…</div></section>
  }

  if (loadError) {
    return (
      <section className="workbench-page">
        <div className="workbench-panel">
          <h2>总览</h2>
          <p className="error-text">{loadError}</p>
          <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
        </div>
      </section>
    )
  }

  return (
    <section className="workbench-page">
      <div className="page-header">
        <h2>总览</h2>
        <span className="card-badge badge-blue">Phase 1</span>
      </div>

      <div className="workbench-grid">
        <div className="workbench-panel">
          <h3>项目概况</h3>
          <p>书名：{model.project?.title || '未命名项目'}</p>
          <p>题材：{model.project?.genre || '未设置'}</p>
          <p>当前章节：{model.progress?.current_chapter || '—'}</p>
        </div>

        <div className="workbench-panel">
          <h3>最近任务</h3>
          {model.recentTasks.length === 0 ? <p className="empty-text">暂无任务记录。</p> : null}
        </div>

        <div className="workbench-panel">
          <h3>最近修改</h3>
          {model.recentChanges.length === 0 ? <p className="empty-text">暂无最近修改。</p> : null}
        </div>

        <div className="workbench-panel">
          <h3>AI 下一步建议</h3>
          {model.nextSuggestions.length === 0 ? <p className="empty-text">后续将在此展示下一步建议。</p> : null}
        </div>
      </div>
    </section>
  )
}
