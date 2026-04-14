export default function TopBar({ model, connected, onSelectPage }) {
  return (
    <header className="workbench-topbar">
      <div>
        <div className="workbench-topbar-title">{model.title}</div>
        <div className="workbench-topbar-subtitle">AI 辅助网文创作工作台</div>
      </div>

      <nav className="workbench-topbar-nav" aria-label="Workbench pages">
        {model.pages.map(page => (
          <button
            key={page.id}
            type="button"
            className={`workbench-nav-button ${model.activePage === page.id ? 'active' : ''}`}
            onClick={() => onSelectPage(page.id)}
          >
            {page.label}
          </button>
        ))}
      </nav>

      <div className="workbench-topbar-status">
        <span className={`status-dot ${connected ? '' : 'disconnected'}`} />
        <span className="workbench-task-badge">{model.taskBadge.label}</span>
      </div>
    </header>
  )
}
