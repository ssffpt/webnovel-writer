import ProjectSwitcher from './ProjectSwitcher.jsx'

export default function TopBar({ model, connected, onSelectPage, projects, currentProjectPath, onSwitchProject, onCreateNew }) {
  return (
    <header className="workbench-topbar">
      <nav className="workbench-topbar-nav" aria-label="Workbench pages">
        {model.pages.map(page => (
          <button
            key={page.id}
            type="button"
            className={`workbench-nav-button ${model.activePage === page.id ? 'active' : ''}`}
            onClick={() => onSelectPage(page.id)}
          >
            {page.number && <span className="workbench-nav-number">{page.number}</span>}
            {page.label}
          </button>
        ))}
      </nav>

      <div className="workbench-topbar-right">
        <div className="workbench-topbar-status">
          <span className={`status-dot ${connected ? '' : 'disconnected'}`} />
          <span className="workbench-task-badge">{model.taskBadge.label}</span>
        </div>
        <ProjectSwitcher
          projects={projects || []}
          currentPath={currentProjectPath}
          onSwitch={onSwitchProject}
          onCreateNew={onCreateNew}
        />
      </div>
    </header>
  )
}
