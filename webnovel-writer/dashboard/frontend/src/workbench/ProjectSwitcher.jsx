import { useState, useEffect, useRef } from 'react'
import { removeProject, renameProject, cleanupProjects } from '../api.js'

export default function ProjectSwitcher({ projects, currentPath, onSwitch, onCreateNew, onProjectsChange }) {
  const [open, setOpen] = useState(false)
  const [showManage, setShowManage] = useState(false)
  const [editingPath, setEditingPath] = useState(null)
  const [editName, setEditName] = useState('')
  const [selectedPaths, setSelectedPaths] = useState(new Set())
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

  function toggleSelect(path) {
    setSelectedPaths(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  function selectAll() {
    if (selectedPaths.size === projects.length) {
      setSelectedPaths(new Set())
    } else {
      setSelectedPaths(new Set(projects.map(p => p.path)))
    }
  }

  async function handleRemove(project, deleteDir) {
    if (!confirm(`确定要${deleteDir ? '彻底删除' : '从列表移除'}项目「${project.name}」？`)) return
    try {
      await removeProject(project.path, deleteDir)
      onProjectsChange?.()
    } catch (err) {
      alert('移除失败：' + (err.message || '未知错误'))
    }
  }

  async function handleBatchRemove(deleteDir) {
    const paths = Array.from(selectedPaths)
    if (paths.length === 0) return
    const action = deleteDir ? '彻底删除' : '从列表移除'
    if (!confirm(`确定要${action}选中的 ${paths.length} 个项目？`)) return
    let success = 0
    let failed = 0
    for (const path of paths) {
      try {
        await removeProject(path, deleteDir)
        success++
      } catch {
        failed++
      }
    }
    setSelectedPaths(new Set())
    onProjectsChange?.()
    if (failed > 0) alert(`${success} 个成功，${failed} 个失败`)
  }

  async function handleRename(project) {
    const newName = editName.trim()
    if (!newName) return
    try {
      await renameProject(project.path, newName)
      setEditingPath(null)
      setEditName('')
      onProjectsChange?.()
    } catch (err) {
      alert('重命名失败：' + (err.message || '未知错误'))
    }
  }

  async function handleCleanup() {
    if (!confirm('清理已删除的项目记录？')) return
    try {
      const result = await cleanupProjects()
      const count = result.removed?.length || 0
      if (count > 0) alert(`已清理 ${count} 个无效记录`)
      onProjectsChange?.()
    } catch (err) {
      alert('清理失败：' + (err.message || '未知错误'))
    }
  }

  function startRename(project) {
    setEditingPath(project.path)
    setEditName(project.name)
  }

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
          {!showManage ? (
            <>
              <div className="project-switcher-footer">
                <button
                  type="button"
                  className="project-switcher-create"
                  onClick={() => { onCreateNew?.(); setOpen(false) }}
                >
                  + 创建新小说
                </button>
                <button
                  type="button"
                  className="project-switcher-manage"
                  onClick={() => setShowManage(true)}
                >
                  管理项目
                </button>
              </div>
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
            </>
          ) : (
            <>
              <div className="project-switcher-manage-header">
                <button type="button" className="project-switcher-back" onClick={() => { setShowManage(false); setSelectedPaths(new Set()) }}>
                  ← 返回
                </button>
                <span>项目管理 ({selectedPaths.size} 选中)</span>
              </div>
              <div className="project-batch-bar">
                <label className="project-batch-label">
                  <input
                    type="checkbox"
                    checked={selectedPaths.size === projects.length && projects.length > 0}
                    onChange={selectAll}
                  />
                  全选
                </label>
                {selectedPaths.size > 0 && (
                  <>
                    <button type="button" className="project-batch-remove" onClick={() => handleBatchRemove(false)}>
                      批量移除
                    </button>
                    <button type="button" className="project-batch-delete" onClick={() => handleBatchRemove(true)}>
                      批量删除
                    </button>
                  </>
                )}
              </div>
              <ul className="project-switcher-list project-switcher-manage-list">
                {projects.map(project => (
                  <li key={project.path} className="project-manage-item">
                    {editingPath === project.path ? (
                      <div className="project-rename-row">
                        <input
                          type="text"
                          value={editName}
                          onChange={e => setEditName(e.target.value)}
                          onKeyDown={e => e.key === 'Enter' && handleRename(project)}
                          autoFocus
                        />
                        <button type="button" onClick={() => handleRename(project)}>保存</button>
                        <button type="button" onClick={() => { setEditingPath(null); setEditName('') }}>取消</button>
                      </div>
                    ) : (
                      <div className="project-manage-row">
                        <label className="project-select-label">
                          <input
                            type="checkbox"
                            checked={selectedPaths.has(project.path)}
                            onChange={() => toggleSelect(project.path)}
                          />
                        </label>
                        <span className="project-manage-name">{project.name}</span>
                        <div className="project-manage-actions">
                          <button type="button" onClick={() => startRename(project)}>重命名</button>
                          <button type="button" onClick={() => handleRemove(project, false)}>移除</button>
                          <button type="button" className="project-delete-danger" onClick={() => handleRemove(project, true)}>删除</button>
                        </div>
                      </div>
                    )}
                  </li>
                ))}
              </ul>
              <div className="project-switcher-footer">
                <button type="button" className="project-switcher-cleanup" onClick={handleCleanup}>
                  清理无效记录
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
