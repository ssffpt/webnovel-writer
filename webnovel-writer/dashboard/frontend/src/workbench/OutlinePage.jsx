import { useEffect, useMemo, useState } from 'react'
import { fetchOutlineTree, readFile, saveFile } from '../api.js'

const FIXED_NODES = [
  { key: 'master', label: '总纲', path: '大纲/总纲.md' },
  { key: 'highlights', label: '爽点规划', path: '大纲/爽点规划.md' },
]

function volumeLabel(vol) {
  return `第${vol.number}卷`
}

function volumeRangeText(vol) {
  if (!vol.chapter_range) return ''
  const [start, end] = vol.chapter_range
  return `${start}-${end}章`
}

export default function OutlinePage({
  loading,
  loadError,
  onRetry,
  onContextChange,
  onPageStateChange,
  cachedSelectedPath = null,
  reloadToken = 0,
  onRunAction,
}) {
  const [treeLoading, setTreeLoading] = useState(true)
  const [treeError, setTreeError] = useState('')
  const [treeData, setTreeData] = useState({ files: [], volumes: [], total_volumes: 0 })
  const [selectedPath, setSelectedPath] = useState(null)
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saveState, setSaveState] = useState('idle')
  const [contentError, setContentError] = useState('')

  // Load outline tree
  useEffect(() => {
    let active = true
    async function loadTree() {
      setTreeLoading(true)
      setTreeError('')
      try {
        const data = await fetchOutlineTree()
        if (!active) return
        setTreeData(data)
        // Auto-select: cached path > first fixed node > null
        if (cachedSelectedPath) {
          setSelectedPath(current => current ?? cachedSelectedPath)
        } else {
          setSelectedPath(current => current ?? FIXED_NODES[0].path)
        }
      } catch (error) {
        if (!active) return
        setTreeError(error instanceof Error ? error.message : '加载大纲树失败')
      } finally {
        if (active) setTreeLoading(false)
      }
    }
    loadTree()
    return () => { active = false }
  }, [reloadToken])

  // Load file content when selectedPath changes
  useEffect(() => {
    if (!selectedPath) {
      setDraft('')
      return
    }
    let active = true
    async function loadContent() {
      setContentError('')
      setSaveState('loading')
      try {
        const payload = await readFile(selectedPath)
        if (!active) return
        setDraft(payload.content || '')
        setDirty(false)
        setSaveState('idle')
      } catch (error) {
        if (!active) return
        setContentError(error instanceof Error ? error.message : '加载大纲内容失败')
        setSaveState('idle')
      }
    }
    loadContent()
    return () => { active = false }
  }, [reloadToken, selectedPath])

  // Sync context to parent
  useEffect(() => {
    onContextChange?.({ page: 'outline', selectedPath, dirty })
    onPageStateChange?.('outline', { selectedPath, dirty })
  }, [dirty, onContextChange, onPageStateChange, selectedPath])

  // Build a display name for the selected file
  const selectedLabel = useMemo(() => {
    if (!selectedPath) return null
    const fixed = FIXED_NODES.find(n => n.path === selectedPath)
    if (fixed) return fixed.label
    const vol = treeData.volumes?.find(v => v.outline_path === selectedPath)
    if (vol) return `${volumeLabel(vol)} 详细大纲`
    // Fallback: extract from path
    const parts = selectedPath.split('/')
    return parts[parts.length - 1].replace(/\.md$/, '')
  }, [selectedPath, treeData.volumes])

  function handleSelectFile(path) {
    if (dirty && selectedPath !== path) {
      if (!window.confirm('当前文件有未保存的修改，切换文件将丢失修改。确定继续？')) return
    }
    setSelectedPath(path)
  }

  async function handleSave() {
    if (!selectedPath) return
    setSaveState('saving')
    try {
      await saveFile(selectedPath, draft)
      setDirty(false)
      setSaveState('saved')
      setTimeout(() => {
        setSaveState(current => (current === 'saved' ? 'idle' : current))
      }, 1200)
    } catch (error) {
      setSaveState('error')
      setContentError(error instanceof Error ? error.message : '保存失败')
    }
  }

  function handleGenerateVolume(vol) {
    onRunAction?.({
      type: 'plan_outline',
      label: `生成第${vol.number}卷大纲`,
      params: { volume: vol.number },
    })
  }

  // --- Render ---

  if (loading || treeLoading) {
    return (
      <section className="workbench-page">
        <div className="workbench-panel">
          <div className="loading-spinner" />
          <p>正在加载大纲工作区…</p>
        </div>
      </section>
    )
  }

  if (loadError || treeError) {
    return (
      <section className="workbench-page">
        <div className="workbench-panel">
          <p className="error-text">{loadError || treeError}</p>
          <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
        </div>
      </section>
    )
  }

  return (
    <section className="workbench-page outline-page-shell">
      <div className="outline-workspace">
        {/* Left: tree sidebar */}
        <aside className="outline-tree workbench-panel">
          <h3>大纲结构</h3>
          <ul className="outline-tree-list">
            {FIXED_NODES.map(node => (
              <li key={node.key}>
                <button
                  type="button"
                  className={`outline-tree-item ${selectedPath === node.path ? 'active' : ''}`}
                  onClick={() => handleSelectFile(node.path)}
                >
                  <span className="tree-icon">📄</span>
                  <span>{node.label}</span>
                </button>
              </li>
            ))}
            {treeData.volumes?.map(vol => (
              <li key={vol.number}>
                {vol.has_outline ? (
                  <button
                    type="button"
                    className={`outline-tree-item ${selectedPath === vol.outline_path ? 'active' : ''}`}
                    onClick={() => handleSelectFile(vol.outline_path)}
                  >
                    <span className="tree-icon">✓</span>
                    <span>{volumeLabel(vol)}</span>
                    <span className="chapter-file-meta">{volumeRangeText(vol)}</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    className="outline-tree-item outline-generate-btn"
                    onClick={() => handleGenerateVolume(vol)}
                  >
                    <span className="tree-icon">＋</span>
                    <span>生成{volumeLabel(vol)}大纲</span>
                    <span className="chapter-file-meta">{volumeRangeText(vol)}</span>
                  </button>
                )}
              </li>
            ))}
          </ul>
          {treeData.total_volumes > 0 && (
            <p className="chapter-file-meta" style={{ marginTop: '10px' }}>
              共 {treeData.total_volumes} 卷
            </p>
          )}
        </aside>

        {/* Right: editor area */}
        <div className="workbench-panel outline-editor-panel">
          <div className="chapter-editor-header">
            <div>
              <h3>{selectedLabel || '未选择大纲文件'}</h3>
              <p className="empty-text">{selectedPath || '请先从左侧选择大纲文件'}</p>
            </div>
            <div className="chapter-editor-actions">
              <span className={`card-badge ${saveState === 'saved' ? 'badge-green' : dirty ? 'badge-amber' : 'badge-blue'}`}>
                {saveState === 'saved' ? '已保存' : dirty ? '未保存' : '已同步'}
              </span>
              <button
                type="button"
                className="workbench-primary-button"
                onClick={handleSave}
                disabled={!selectedPath || saveState === 'saving' || saveState === 'loading'}
              >
                {saveState === 'saving' ? '保存中…' : '保存'}
              </button>
            </div>
          </div>

          <div className="chapter-placeholder-actions">
            <button type="button" className="workbench-nav-button disabled-action-btn" disabled title="即将支持">
              生成卷纲 🔒
            </button>
            <button type="button" className="workbench-nav-button disabled-action-btn" disabled title="即将支持">
              生成章纲 🔒
            </button>
          </div>

          {contentError ? <p className="error-text">{contentError}</p> : null}

          <textarea
            className="chapter-editor-textarea"
            value={draft}
            onChange={event => {
              setDraft(event.target.value)
              setDirty(true)
            }}
            placeholder="在这里编辑总纲、卷纲或章纲…"
            disabled={!selectedPath}
          />
        </div>
      </div>
    </section>
  )
}
