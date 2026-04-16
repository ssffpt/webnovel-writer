import { useState, useEffect, useRef } from 'react'

export default function ProjectSwitcher({ projects, currentPath, onSwitch, onCreateNew }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function handleClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const current = projects.find(p => p.path === currentPath)

  return (
    <div className="project-switcher" ref={ref}>
      <button
        type="button"
        className="project-switcher-trigger"
        onClick={() => setOpen(prev => !prev)}
      >
        <span className="project-switcher-label">
          {current ? current.name : '选择项目'}
        </span>
        <span className="project-switcher-arrow">▾</span>
      </button>

      {open && (
        <div className="project-switcher-dropdown">
          {projects.length === 0 ? (
            <div className="project-switcher-empty">暂无项目</div>
          ) : (
            <ul className="project-switcher-list">
              {projects.map(project => (
                <li key={project.path}>
                  <button
                    type="button"
                    className={`project-switcher-item ${project.path === currentPath ? 'active' : ''}`}
                    onClick={() => { onSwitch?.(project.path); setOpen(false) }}
                  >
                    <span className="project-switcher-item-name">{project.name}</span>
                    <span className="project-switcher-item-meta">
                      {project.genre || ''}{project.current_chapter ? ` · 第${project.current_chapter}章` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div className="project-switcher-footer">
            <button
              type="button"
              className="project-switcher-create"
              onClick={() => { onCreateNew?.(); setOpen(false) }}
            >
              + 创建新小说
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
