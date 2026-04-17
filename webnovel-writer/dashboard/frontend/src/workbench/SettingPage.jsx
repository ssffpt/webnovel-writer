import { useEffect, useMemo, useState } from 'react'
import { fetchJSON, readFile, saveFile } from '../api.js'
import { ENTITY_TYPE_MAP, ENTITY_FILTER_CATEGORIES, FILTER_TO_DB_TYPE } from './data.js'

export default function SettingPage({ loading, loadError, onRetry, onContextChange, onPageStateChange, cachedSelectedPath = null, reloadToken = 0 }) {
  const [entitiesLoading, setEntitiesLoading] = useState(true)
  const [entitiesError, setEntitiesError] = useState('')
  const [entities, setEntities] = useState([])
  const [filter, setFilter] = useState('全部')
  const [selectedId, setSelectedId] = useState(null)
  const [draft, setDraft] = useState('')
  const [dirty, setDirty] = useState(false)
  const [saveState, setSaveState] = useState('idle')
  const [contentError, setContentError] = useState('')
  const [pendingSwitchId, setPendingSwitchId] = useState(null)

  // Load all entities once
  useEffect(() => {
    let active = true
    async function loadEntities() {
      setEntitiesLoading(true)
      setEntitiesError('')
      try {
        const data = await fetchJSON('/api/entities')
        const list = data.entities || data || []
        if (!active) return
        setEntities(list)
        if (cachedSelectedPath) {
          const match = list.find(e => e.file_path === cachedSelectedPath)
          if (match) setSelectedId(current => current ?? match.id)
        } else if (list.length > 0) {
          setSelectedId(current => current ?? list[0].id)
        }
      } catch (error) {
        if (!active) return
        setEntitiesError(error instanceof Error ? error.message : '加载实体列表失败')
      } finally {
        if (active) setEntitiesLoading(false)
      }
    }
    loadEntities()
    return () => { active = false }
  }, [reloadToken])

  // Count by frontend filter label
  const counts = useMemo(() => {
    const map = { '全部': entities.length }
    for (const e of entities) {
      const label = ENTITY_TYPE_MAP[e.type]?.label || e.type
      map[label] = (map[label] || 0) + 1
    }
    return map
  }, [entities])

  // Filtered entities
  const visibleEntities = useMemo(() => {
    if (filter === '全部') return entities
    const dbType = FILTER_TO_DB_TYPE[filter]
    return entities.filter(e => e.type === dbType)
  }, [filter, entities])

  // Auto-select first visible entity when filter changes
  useEffect(() => {
    if (visibleEntities.length === 0) {
      setSelectedId(null)
      return
    }
    if (!visibleEntities.some(e => e.id === selectedId)) {
      setSelectedId(visibleEntities[0].id)
    }
  }, [selectedId, visibleEntities])

  const selectedEntity = useMemo(
    () => entities.find(e => e.id === selectedId) ?? null,
    [selectedId, entities],
  )

  // Load file content when selection changes
  useEffect(() => {
    if (!selectedEntity?.file_path) {
      setDraft('')
      return
    }
    let active = true
    async function loadContent() {
      setContentError('')
      setSaveState('loading')
      try {
        const payload = await readFile(selectedEntity.file_path)
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
    return () => { active = false }
  }, [reloadToken, selectedEntity?.file_path])

  // Sync context and page state
  useEffect(() => {
    onContextChange?.({
      page: 'settings',
      selectedPath: selectedEntity?.file_path ?? null,
      dirty,
    })
    onPageStateChange?.('settings', { selectedPath: selectedEntity?.file_path ?? null, dirty })
  }, [dirty, onContextChange, onPageStateChange, selectedEntity?.file_path])

  function handleSelectEntity(id) {
    if (dirty && selectedId !== id) {
      setPendingSwitchId(id)
      return
    }
    setSelectedId(id)
  }

  function confirmSwitchEntity() {
    if (pendingSwitchId !== null) {
      setSelectedId(pendingSwitchId)
    }
    setPendingSwitchId(null)
  }

  function cancelSwitchEntity() {
    setPendingSwitchId(null)
  }

  async function handleSave() {
    if (!selectedEntity?.file_path) return
    setSaveState('saving')
    try {
      await saveFile(selectedEntity.file_path, draft)
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

  const selectedLabel = selectedEntity
    ? (ENTITY_TYPE_MAP[selectedEntity.type]?.label || selectedEntity.type)
    : filter

  return (
    <section className="workbench-page chapter-page-shell">
      <div className="page-header">
        <h2>设定</h2>
        <span className="card-badge badge-cyan">真实工作区</span>
      </div>

      {(loading || entitiesLoading) && <div className="workbench-panel">正在加载设定工作区…</div>}
      {(loadError || entitiesError) && (
        <div className="workbench-panel">
          <p className="error-text">{loadError || entitiesError}</p>
          <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
        </div>
      )}

      <div className="chapter-workspace setting-workspace">
        <aside className="workbench-panel setting-list-panel">
          <h3>实体分类</h3>
          <div className="setting-category-list">
            {ENTITY_FILTER_CATEGORIES.map(cat => (
              <button
                key={cat}
                type="button"
                className={`setting-category-button ${filter === cat ? 'active' : ''}`}
                onClick={() => setFilter(cat)}
              >
                {cat}({counts[cat] || 0})
              </button>
            ))}
          </div>

          <div className="chapter-file-list settings-file-list">
            {visibleEntities.length === 0 ? (
              <p className="empty-text">当前分类下暂无实体。</p>
            ) : (
              visibleEntities.map(entity => {
                const info = ENTITY_TYPE_MAP[entity.type]
                return (
                  <button
                    key={entity.id}
                    type="button"
                    className={`setting-entity-card ${selectedId === entity.id ? 'active' : ''}`}
                    onClick={() => handleSelectEntity(entity.id)}
                  >
                    <span className="setting-entity-name">
                      <span className="setting-entity-icon">{info?.icon || '📄'}</span>
                      {entity.canonical_name}
                    </span>
                    <span className="setting-entity-desc">{entity.desc || ''}</span>
                  </button>
                )
              })
            )}
          </div>
        </aside>

        <div className="workbench-panel chapter-editor-panel">
          <div className="chapter-editor-header">
            <div>
              <h3>{selectedEntity?.canonical_name || '未选择实体'}</h3>
              <p className="empty-text">{selectedEntity?.file_path || '请先从左侧选择实体'}</p>
            </div>
            <div className="chapter-editor-actions">
              <span className="card-badge badge-cyan">{selectedLabel}</span>
              <span className={`card-badge ${saveState === 'saved' ? 'badge-green' : dirty ? 'badge-amber' : 'badge-blue'}`}>
                {saveState === 'saved' ? '已保存' : dirty ? '未保存' : '已同步'}
              </span>
              <button
                type="button"
                className="workbench-primary-button"
                onClick={handleSave}
                disabled={!selectedEntity?.file_path || saveState === 'saving' || saveState === 'loading'}
              >
                {saveState === 'saving' ? '保存中…' : '保存'}
              </button>
            </div>
          </div>

          <div className="chapter-placeholder-actions">
            <button type="button" className="workbench-nav-button disabled-action-btn" disabled>检查冲突 🔒</button>
          </div>

          {contentError ? <p className="error-text">{contentError}</p> : null}

          <textarea
            className="chapter-editor-textarea"
            value={draft}
            onChange={event => {
              setDraft(event.target.value)
              setDirty(true)
            }}
            placeholder="在这里编辑人物、势力、地点或招式设定…"
            disabled={!selectedEntity?.file_path}
          />
        </div>
      </div>

      {pendingSwitchId !== null && (
        <div className="conflict-dialog-overlay">
          <div className="conflict-dialog">
            <h3>存在未保存内容</h3>
            <p>当前文件有未保存的修改，切换将丢失修改。确定继续？</p>
            <div className="conflict-dialog-actions">
              <button type="button" className="workbench-primary-button" onClick={confirmSwitchEntity}>继续</button>
              <button type="button" className="workbench-nav-button" onClick={cancelSwitchEntity}>取消</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
