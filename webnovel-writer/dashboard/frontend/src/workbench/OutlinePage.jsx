import { useEffect, useMemo, useState } from 'react'
import { fetchFileTree, readFile, saveFile } from '../api.js'

function flattenFiles(nodes = []) {
  const files = []
  for (const node of nodes) {
    if (node.type === 'file') {
      files.push(node)
    } else if (node.type === 'dir') {
      files.push(...flattenFiles(node.children || []))
    }
  }
  return files
}

function inferOutlineKind(path = '') {
  if (path.includes('总纲')) return '总纲'
  if (path.includes('卷')) return '卷纲'
  if (path.includes('章') || path.includes('章节')) return '章纲'
  return '大纲文件'
}

export default function OutlinePage({ loading, loadError, onRetry, onContextChange, onPageStateChange, cachedSelectedPath = null, reloadToken = 0 }) {
  const [treeLoading, setTreeLoading] = useState(true)
  const [treeError, setTreeError] = useState('')
  const [outlineFiles, setOutlineFiles] = useState([])
  const [selectedPath, setSelectedPath] = useState(null)
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saveState, setSaveState] = useState('idle')
  const [contentError, setContentError] = useState('')

  useEffect(() => {
    let active = true
    async function loadTree() {
      setTreeLoading(true)
      setTreeError('')
      try {
        const tree = await fetchFileTree()
        const files = flattenFiles(tree['大纲'] || [])
        if (!active) return
        setOutlineFiles(files)
        if (cachedSelectedPath && files.some(f => f.path === cachedSelectedPath)) {
          setSelectedPath(current => current ?? cachedSelectedPath)
        } else {
          setSelectedPath(current => current ?? files[0]?.path ?? null)
        }
      } catch (error) {
        if (!active) return
        setTreeError(error instanceof Error ? error.message : '加载大纲列表失败')
      } finally {
        if (active) setTreeLoading(false)
      }
    }
    loadTree()
    return () => {
      active = false
    }
  }, [reloadToken])

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
    return () => {
      active = false
    }
  }, [reloadToken, selectedPath])

  useEffect(() => {
    onContextChange?.({
      page: 'outline',
      selectedPath,
      dirty,
    })
    onPageStateChange?.('outline', { selectedPath, dirty })
  }, [dirty, onContextChange, onPageStateChange, selectedPath])

  const selectedFile = useMemo(
    () => outlineFiles.find(file => file.path === selectedPath) ?? null,
    [outlineFiles, selectedPath],
  )

  function handleSelectFile(path) {
    if (dirty && selectedPath !== path && !window.confirm('当前文件有未保存的修改，切换文件将丢失修改。确定继续？')) {
      return
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

  const selectedKind = inferOutlineKind(selectedPath)

  return (
    <section className="workbench-page chapter-page-shell">
      <div className="page-header">
        <h2>大纲</h2>
        <span className="card-badge badge-purple">真实工作区</span>
      </div>

      {(loading || treeLoading) && <div className="workbench-panel">正在加载大纲工作区…</div>}
      {(loadError || treeError) && (
        <div className="workbench-panel">
          <p className="error-text">{loadError || treeError}</p>
          <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载摘要</button>
        </div>
      )}

      <div className="chapter-workspace">
        <aside className="workbench-panel chapter-list-panel">
          <h3>大纲文件</h3>
          {outlineFiles.length === 0 ? (
            <p className="empty-text">大纲目录下暂无文件。</p>
          ) : (
            <div className="chapter-file-list">
              {outlineFiles.map(file => (
                <button
                  key={file.path}
                  type="button"
                  className={`chapter-file-button ${selectedPath === file.path ? 'active' : ''}`}
                  onClick={() => handleSelectFile(file.path)}
                >
                  <span>{file.name}</span>
                  <span className="chapter-file-meta">{inferOutlineKind(file.path)}</span>
                </button>
              ))}
            </div>
          )}
        </aside>

        <div className="workbench-panel chapter-editor-panel">
          <div className="chapter-editor-header">
            <div>
              <h3>{selectedFile?.name || '未选择大纲文件'}</h3>
              <p className="empty-text">{selectedPath || '请先从左侧选择大纲文件'}</p>
            </div>
            <div className="chapter-editor-actions">
              <span className="card-badge badge-cyan">{selectedKind}</span>
              <span className={`card-badge ${dirty ? 'badge-amber' : 'badge-blue'}`}>
                {dirty ? '未保存' : '已同步'}
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
            <button type="button" className="workbench-nav-button" disabled>生成卷纲</button>
            <button type="button" className="workbench-nav-button" disabled>生成章纲</button>
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
