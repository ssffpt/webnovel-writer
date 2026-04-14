export default function PlaceholderPage({ title, description, loading, loadError, onRetry }) {
  return (
    <section className="workbench-page">
      <div className="page-header">
        <h2>{title}</h2>
        <span className="card-badge badge-amber">占位页</span>
      </div>

      <div className="workbench-panel">
        <p>{description}</p>
        {loading ? <p className="empty-text">工作台摘要加载中…</p> : null}
        {loadError ? (
          <>
            <p className="error-text">{loadError}</p>
            <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
          </>
        ) : null}
      </div>
    </section>
  )
}
