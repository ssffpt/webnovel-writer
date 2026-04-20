import { useCallback, useEffect, useMemo, useState } from 'react'
import { fetchFileTree, readFile, saveFile } from '../api.js'
import WriteFlow from './WriteFlow.jsx'

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

function extractChapterNumber(fileName = '') {
  const match = String(fileName).match(/(\d+)/)
  return match ? Number(match[1]) : null
}

export default function ChapterPage({
  loading,
  loadError,
  onRetry,
  onContextChange,
  onPageStateChange,
  cachedSelectedPath = null,
  reloadToken = 0,
  onFocusModeChange,
}) {
  const [treeLoading, setTreeLoading] = useState(true)
  const [treeError, setTreeError] = useState('')
  const [chapterFiles, setChapterFiles] = useState([])
  const [selectedPath, setSelectedPath] = useState(null)
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saveState, setSaveState] = useState('idle')
  const [loadContentError, setLoadContentError] = useState('')
  const [focusMode, setFocusMode] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [pendingSwitchPath, setPendingSwitchPath] = useState(null)
  const [editMode, setEditMode] = useState('manual')

  // Word count (Chinese: count non-whitespace characters)
  const wordCount = useMemo(() => draft.replace(/\s/g, '').length, [draft])

  // Reverse order chapter list (newest first)
  const reversedFiles = useMemo(() => chapterFiles.slice().reverse(), [chapterFiles])

  // Next chapter number for "写第N章" button（按最大章节号+1，支持编号间隙）
  const nextChapterNum = useMemo(() => {
    const maxNum = chapterFiles.reduce((max, file) => {
      const num = extractChapterNumber(file.name)
      return Number.isFinite(num) ? Math.max(max, num) : max
    }, 0)
    return maxNum + 1
  }, [chapterFiles])

  // --- ESC to exit focus mode ---
  useEffect(() => {
    if (!focusMode) return
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setFocusMode(false)
        onFocusModeChange?.(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [focusMode, onFocusModeChange])

  // --- File tree loading ---
  useEffect(() => {
    let active = true
    async function loadTree() {
      setTreeLoading(true)
      setTreeError('')
      try {
        const tree = await fetchFileTree()
        const files = flattenFiles(tree['正文'] || [])
        if (!active) return
        setChapterFiles(files)
        if (cachedSelectedPath && files.some(f => f.path === cachedSelectedPath)) {
          setSelectedPath(current => current ?? cachedSelectedPath)
        } else {
          setSelectedPath(current => current ?? files[0]?.path ?? null)
        }
      } catch (error) {
        if (!active) return
        setTreeError(error instanceof Error ? error.message : '加载章节列表失败')
      } finally {
        if (active) setTreeLoading(false)
      }
    }
    loadTree()
    return () => { active = false }
  }, [reloadToken])

  // --- File content loading ---
  useEffect(() => {
    if (!selectedPath) {
      setDraft('')
      return
    }
    let active = true
    async function loadContent() {
      setLoadContentError('')
      setSaveState('loading')
      try {
        const payload = await readFile(selectedPath)
        if (!active) return
        setDraft(payload.content || '')
        setDirty(false)
        setSaveState('idle')
      } catch (error) {
        if (!active) return
        setLoadContentError(error instanceof Error ? error.message : '加载章节内容失败')
        setSaveState('idle')
      }
    }
    loadContent()
    return () => { active = false }
  }, [reloadToken, selectedPath])

  // --- Context sync ---
  useEffect(() => {
    onContextChange?.({
      page: 'chapters',
      selectedPath,
      dirty,
    })
    onPageStateChange?.('chapters', { selectedPath, dirty })
  }, [dirty, onContextChange, onPageStateChange, selectedPath])

  const selectedFile = useMemo(
    () => chapterFiles.find(file => file.path === selectedPath) ?? null,
    [chapterFiles, selectedPath],
  )

  function handleSelectFile(path) {
    if (dirty && selectedPath !== path) {
      setPendingSwitchPath(path)
      return
    }
    setSelectedPath(path)
  }

  function confirmSwitchFile() {
    if (pendingSwitchPath) {
      setSelectedPath(pendingSwitchPath)
    }
    setPendingSwitchPath(null)
  }

  function cancelSwitchFile() {
    setPendingSwitchPath(null)
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
      setLoadContentError(error instanceof Error ? error.message : '保存失败')
    }
  }

  const handleToggleFocusMode = useCallback(() => {
    setFocusMode(prev => {
      const next = !prev
      onFocusModeChange?.(next)
      return next
    })
  }, [onFocusModeChange])

  const handleToggleSidebar = useCallback(() => {
    setSidebarCollapsed(prev => !prev)
  }, [])

  // --- Empty state ---
  if (!loading && !treeLoading && !loadError && !treeError && chapterFiles.length === 0) {
    return (
      <section className="chapter-page-shell chapter-page-empty">
        <div className="chapter-empty-sidebar">
          <p className="empty-text">还没有章节</p>
        </div>
        <div className="chapter-empty-main">
          <div className="chapter-empty-prompt">
            <p>开始写第1章吧！</p>
            <button
              type="button"
              className="workbench-primary-button"
              onClick={() => setSelectedPath(null)}
            >
              ＋ 写第1章
            </button>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className={`chapter-page-shell${focusMode ? ' focus-mode' : ''}${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      {(loading || treeLoading) && <div className="workbench-panel">正在加载章节工作区…</div>}
      {(loadError || treeError) && (
        <div className="workbench-panel">
          <p className="error-text">{loadError || treeError}</p>
          <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载摘要</button>
        </div>
      )}

      <div className="chapter-workspace">
        {/* Left sidebar — 140px collapsible */}
        {!focusMode && (
          <aside className={`chapter-list-panel${sidebarCollapsed ? ' collapsed' : ''}`}>
            {!sidebarCollapsed ? (
              <>
                <div className="chapter-list-header">
                  <h3>章节</h3>
                  <button
                    type="button"
                    className="chapter-sidebar-toggle"
                    onClick={handleToggleSidebar}
                    title="收起侧栏"
                  >
                    ◀
                  </button>
                </div>
                <div className="chapter-file-list">
                  {reversedFiles.map(file => (
                    <button
                      key={file.path}
                      type="button"
                      className={`chapter-file-button ${selectedPath === file.path ? 'active' : ''}`}
                      onClick={() => handleSelectFile(file.path)}
                    >
                      <span>{file.name}</span>
                      <span className="chapter-file-meta">{file.size ?? 0} B</span>
                    </button>
                  ))}
                </div>
                <div className="chapter-list-footer">
                  <button
                    type="button"
                    className="workbench-primary-button chapter-add-button"
                    onClick={() => setSelectedPath(null)}
                  >
                    ＋ 写第{nextChapterNum}章
                  </button>
                </div>
              </>
            ) : (
              <button
                type="button"
                className="chapter-sidebar-toggle expand"
                onClick={handleToggleSidebar}
                title="展开侧栏"
              >
                ▶
              </button>
            )}
          </aside>
        )}

        {/* Right editor */}
        <div className="chapter-editor-panel">
          <div className="chapter-editor-header">
            <div className="chapter-editor-path">
              {selectedPath || '未选择章节'}
            </div>
            <div className="chapter-editor-actions">
              <button
                type="button"
                className={`chapter-focus-button${focusMode ? ' active' : ''}`}
                onClick={handleToggleFocusMode}
                title={focusMode ? '退出专注模式 (ESC)' : '专注模式'}
              >
                {focusMode ? '退出专注' : '专注'}
              </button>
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

          <div className="mode-toggle">
            <button
              type="button"
              className={editMode === 'manual' ? 'active' : ''}
              onClick={() => setEditMode('manual')}
            >
              手动编辑
            </button>
            <button
              type="button"
              className={editMode === 'ai' ? 'active' : ''}
              onClick={() => setEditMode('ai')}
            >
              AI 创作
            </button>
          </div>

          {editMode === 'ai' ? (
            <WriteFlow
              projectRoot={selectedPath ? selectedPath.split('/chapters/')[0] : ''}
              chapterNum={selectedPath ? extractChapterNumber(selectedPath) || 1 : 1}
              onCompleted={(text) => {
                setEditMode('manual')
                setDraft(text)
                setDirty(true)
              }}
              onCancelled={() => setEditMode('manual')}
            />
          ) : (
            <>
              {loadContentError ? <p className="error-text">{loadContentError}</p> : null}

              <textarea
                className="chapter-editor-textarea"
                value={draft}
                onChange={event => {
                  setDraft(event.target.value)
                  setDirty(true)
                }}
                placeholder="在这里编辑章节正文…"
                disabled={!selectedPath}
              />
            </>
          )}

          <div className="chapter-status-bar">
            <span className="chapter-word-count">{wordCount} 字</span>
            {selectedFile && <span className="chapter-file-meta">{selectedFile.name}</span>}
          </div>
        </div>
      </div>

      {pendingSwitchPath && (
        <div className="conflict-dialog-overlay">
          <div className="conflict-dialog">
            <h3>存在未保存内容</h3>
            <p>当前文件有未保存的修改，切换文件将丢失修改。确定继续？</p>
            <div className="conflict-dialog-actions">
              <button type="button" className="workbench-primary-button" onClick={confirmSwitchFile}>继续</button>
              <button type="button" className="workbench-nav-button" onClick={cancelSwitchFile}>取消</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
