import { useEffect, useMemo, useState } from 'react'
import { fetchFileTree, readFile, saveFile } from '../api.js'

const CATEGORIES = ['全部', '人物', '势力', '地点', '世界观']

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

function inferCategory(path = '') {
  const text = path.toLowerCase()
  if (text.includes('人物') || text.includes('角色') || text.includes('主角')) return '人物'
  if (text.includes('势力') || text.includes('宗门')) return '势力'
  if (text.includes('地点') || text.includes('地理') || text.includes('地图')) return '地点'
  if (text.includes('世界') || text.includes('体系') || text.includes('设定')) return '世界观'
  return '全部'
}

export default function SettingPage({ loading, loadError, onRetry, onContextChange, onPageStateChange, cachedSelectedPath = null, reloadToken = 0 }) {
  const [treeLoading, setTreeLoading] = useState(true)
  const [treeError, setTreeError] = useState('')
  const [settingFiles, setSettingFiles] = useState([])
  const [category, setCategory] = useState('全部')
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
        const files = flattenFiles(tree['设定集'] || [])
        if (!active) return
        setSettingFiles(files)
        if (cachedSelectedPath && files.some(f => f.path === cachedSelectedPath)) {
          setSelectedPath(current => current ?? cachedSelectedPath)
        } else {
          setSelectedPath(current => current ?? files[0]?.path ?? null)
        }
      } catch (error) {
        if (!active) return
        setTreeError(error instanceof Error ? error.message : '加载设定列表失败')
      } finally {
        if (active) setTreeLoading(false)
      }
    }
    loadTree()
    return () => {
      active = false
    }
  }, [reloadToken])

  const visibleFiles = useMemo(() => {
    if (category === '全部') return settingFiles
    return settingFiles.filter(file => inferCategory(file.path) === category)
  }, [category, settingFiles])

  useEffect(() => {
    if (visibleFiles.length === 0) {
      setSelectedPath(null)
      return
    }
    if (!visibleFiles.some(file => file.path === selectedPath)) {
      setSelectedPath(visibleFiles[0].path)
    }
  }, [selectedPath, visibleFiles])

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
        setContentError(error instanceof Error ? error.message : '加载设定内容失败')
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
      page: 'settings',
      selectedPath,
      dirty,
    })
    onPageStateChange?.('settings', { selectedPath, dirty })
  }, [dirty, onContextChange, onPageStateChange, selectedPath])

  const selectedFile = useMemo(
    () => settingFiles.find(file => file.path === selectedPath) ?? null,
    [selectedPath, settingFiles],
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

  const selectedCategory = selectedFile ? inferCategory(selectedFile.path) : category

  return (
    <section className="workbench-page chapter-page-shell">
      <div className="page-header">
        <h2>设定</h2>
        <span className="card-badge badge-cyan">真实工作区</span>
      </div>

      {(loading || treeLoading) && <div className="workbench-panel">正在加载设定工作区…</div>}
      {(loadError || treeError) && (
        <div className="workbench-panel">
          <p className="error-text">{loadError || treeError}</p>
          <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载摘要</button>
        </div>
      )}

      <div className="chapter-workspace">
        <aside className="workbench-panel chapter-list-panel">
          <h3>设定分类</h3>
          <div className="setting-category-list">
            {CATEGORIES.map(item => (
              <button
                key={item}
                type="button"
                className={`setting-category-button ${category === item ? 'active' : ''}`}
                onClick={() => setCategory(item)}
              >
                {item}
              </button>
            ))}
          </div>

          <div className="chapter-file-list settings-file-list">
            {visibleFiles.length === 0 ? (
              <p className="empty-text">当前分类下暂无设定文件。</p>
            ) : (
              visibleFiles.map(file => (
                <button
                  key={file.path}
                  type="button"
                  className={`chapter-file-button ${selectedPath === file.path ? 'active' : ''}`}
                  onClick={() => handleSelectFile(file.path)}
                >
                  <span>{file.name}</span>
                  <span className="chapter-file-meta">{inferCategory(file.path)}</span>
                </button>
              ))
            )}
          </div>
        </aside>

        <div className="workbench-panel chapter-editor-panel">
          <div className="chapter-editor-header">
            <div>
              <h3>{selectedFile?.name || '未选择设定文件'}</h3>
              <p className="empty-text">{selectedPath || '请先从左侧选择设定文件'}</p>
            </div>
            <div className="chapter-editor-actions">
              <span className="card-badge badge-cyan">{selectedCategory}</span>
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
            <button type="button" className="workbench-nav-button" disabled>检查冲突</button>
          </div>

          {contentError ? <p className="error-text">{contentError}</p> : null}

          <textarea
            className="chapter-editor-textarea"
            value={draft}
            onChange={event => {
              setDraft(event.target.value)
              setDirty(true)
            }}
            placeholder="在这里编辑人物、势力、地点或世界观设定…"
            disabled={!selectedPath}
          />
        </div>
      </div>
    </section>
  )
}
