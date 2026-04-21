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

  // Query tab state
  const [activeTab, setActiveTab] = useState('entity')
  const [queryForeshadowing, setQueryForeshadowing] = useState(null)
  const [queryGoldenFinger, setQueryGoldenFinger] = useState(null)
  const [queryRhythm, setQueryRhythm] = useState(null)
  const [queryDebt, setQueryDebt] = useState(null)
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryError, setQueryError] = useState('')

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

  // Load query tab data when tab changes
  useEffect(() => {
    if (activeTab === 'entity') return
    let active = true
    setQueryLoading(true)
    setQueryError('')
    async function loadQueryData() {
      try {
        let data
        if (activeTab === 'foreshadowing') {
          data = await fetchJSON('/api/query/foreshadowing')
        } else if (activeTab === 'golden-finger') {
          data = await fetchJSON('/api/query/golden-finger')
        } else if (activeTab === 'rhythm') {
          data = await fetchJSON('/api/query/rhythm')
        } else if (activeTab === 'debt') {
          data = await fetchJSON('/api/query/debt')
        }
        if (!active) return
        if (activeTab === 'foreshadowing') setQueryForeshadowing(data)
        else if (activeTab === 'golden-finger') setQueryGoldenFinger(data)
        else if (activeTab === 'rhythm') setQueryRhythm(data)
        else if (activeTab === 'debt') setQueryDebt(data)
      } catch (error) {
        if (!active) return
        setQueryError(error instanceof Error ? error.message : '加载数据失败')
      } finally {
        if (active) setQueryLoading(false)
      }
    }
    loadQueryData()
    return () => { active = false }
  }, [activeTab])

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

          {/* Query Tab Buttons */}
          <div className="query-tab-bar">
            <button
              type="button"
              className={`query-tab-btn ${activeTab === 'entity' ? 'active' : ''}`}
              onClick={() => setActiveTab('entity')}
            >实体</button>
            <button
              type="button"
              className={`query-tab-btn ${activeTab === 'foreshadowing' ? 'active' : ''}`}
              onClick={() => setActiveTab('foreshadowing')}
            >伏笔</button>
            <button
              type="button"
              className={`query-tab-btn ${activeTab === 'golden-finger' ? 'active' : ''}`}
              onClick={() => setActiveTab('golden-finger')}
            >金手指</button>
            <button
              type="button"
              className={`query-tab-btn ${activeTab === 'rhythm' ? 'active' : ''}`}
              onClick={() => setActiveTab('rhythm')}
            >节奏</button>
            <button
              type="button"
              className={`query-tab-btn ${activeTab === 'debt' ? 'active' : ''}`}
              onClick={() => setActiveTab('debt')}
            >债务</button>
          </div>
        </aside>

        {/* Right panel: entity editor or query tabs */}
        <div className="workbench-panel chapter-editor-panel">
          {activeTab === 'entity' ? (
            <>
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
            </>
          ) : activeTab === 'foreshadowing' ? (
            <ForeshadowingTab data={queryForeshadowing} loading={queryLoading} error={queryError} onRetry={() => setActiveTab('foreshadowing')} />
          ) : activeTab === 'golden-finger' ? (
            <GoldenFingerTab data={queryGoldenFinger} loading={queryLoading} error={queryError} onRetry={() => setActiveTab('golden-finger')} />
          ) : activeTab === 'rhythm' ? (
            <RhythmTab data={queryRhythm} loading={queryLoading} error={queryError} onRetry={() => setActiveTab('rhythm')} />
          ) : activeTab === 'debt' ? (
            <DebtTab data={queryDebt} loading={queryLoading} error={queryError} onRetry={() => setActiveTab('debt')} />
          ) : null}
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

// ─── ForeshadowingTab ───
function ForeshadowingTab({ data, loading, error, onRetry }) {
  if (loading) return <div className="query-loading">加载中…</div>
  if (error) return (
    <div className="query-error">
      <p className="error-text">{error}</p>
      <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
    </div>
  )
  if (!data) return <div className="query-empty">暂无数据</div>

  const { stats = {}, foreshadowing = [], by_tier = {} } = data

  const urgencyColor = (urgency) => {
    if (urgency >= 0.8) return 'var(--accent-red)'
    if (urgency >= 0.5) return 'var(--accent-amber)'
    return 'var(--accent-green)'
  }

  const statusLabel = (status) => ({
    planted: '待揭开',
    revealed: '已揭开',
  })[status] || status

  const tierLabel = { chapter: '章级', volume: '卷级', book: '书级' }

  return (
    <div className="query-tab-content foreshadowing-tab">
      <h3>伏笔查询</h3>
      <div className="foreshadowing-stats">
        <span className="stat-item">总数: <strong>{stats.total ?? 0}</strong></span>
        <span className="stat-item stat-green">已揭开: <strong>{stats.revealed ?? 0}</strong></span>
        <span className="stat-item stat-amber">待揭开: <strong>{stats.planted ?? 0}</strong></span>
        <span className="stat-item stat-red">逾期: <strong>{stats.overdue ?? 0}</strong></span>
      </div>

      {['chapter', 'volume', 'book'].map(tier => {
        const items = by_tier[tier] || []
        if (items.length === 0) return null
        return (
          <div key={tier} className="foreshadowing-tier-group">
            <h4 className="tier-title">{tierLabel[tier]} ({items.length})</h4>
            {items.map(item => (
              <div key={item.id} className="foreshadowing-item">
                <div className="foreshadowing-item-header">
                  <span className="foreshadowing-title">{item.title || item.id}</span>
                  <span
                    className="foreshadowing-status-badge"
                    style={{ background: statusLabel(item.status) === '已揭开' ? 'var(--accent-green)' : 'var(--text-mute)' }}
                  >
                    {statusLabel(item.status)}
                  </span>
                </div>
                <div className="foreshadowing-meta">
                  <span>埋入: 第{item.plant_chapter}章</span>
                  <span>预期揭开: 第{item.reveal_chapter}章</span>
                  <span>剩余: {item.chapters_remaining}章</span>
                </div>
                <div className="foreshadowing-urgency-bar">
                  <div
                    className="foreshadowing-urgency-fill"
                    style={{ width: `${Math.min((item.urgency || 0) * 100, 100)}%`, background: urgencyColor(item.urgency || 0) }}
                  />
                </div>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

// ─── GoldenFingerTab ───
function GoldenFingerTab({ data, loading, error, onRetry }) {
  if (loading) return <div className="query-loading">加载中…</div>
  if (error) return (
    <div className="query-error">
      <p className="error-text">{error}</p>
      <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
    </div>
  )
  if (!data || !data.golden_finger) return <div className="query-empty">暂无金手指数据</div>

  const gf = data.golden_finger
  const cooldown = gf.cooldown_status || {}

  return (
    <div className="query-tab-content golden-finger-tab">
      <h3>金手指状态</h3>
      <div className="golden-finger-header">
        <div className="gf-name-type">
          <span className="gf-name">{gf.name || '未知金手指'}</span>
          <span className="card-badge badge-cyan">{gf.type}</span>
        </div>
        <div className="gf-level-info">
          Lv.{gf.level}/{gf.max_level}
        </div>
      </div>

      {/* Progress bar */}
      <div className="gf-progress-section">
        <div className="gf-progress-bar">
          <div className="gf-progress-fill" style={{ width: `${gf.progress_percent || 0}%` }} />
        </div>
        <span className="gf-progress-label">{gf.progress_percent || 0}%</span>
      </div>

      {/* Current effects */}
      <div className="gf-section">
        <h4>当前效果</h4>
        {gf.current_effects && gf.current_effects.length > 0 ? (
          <ul className="gf-effect-list">
            {gf.current_effects.map((effect, i) => (
              <li key={i}>{effect}</li>
            ))}
          </ul>
        ) : <p className="empty-text">暂无效果</p>}
      </div>

      {/* Cooldown status */}
      <div className="gf-section">
        <h4>冷却状态</h4>
        {cooldown.active ? (
          <div className="gf-cooldown-active">
            <span className="cooldown-badge">冷却中</span>
            <span>剩余 {cooldown.remaining_chapters} 章</span>
            {cooldown.recent_chapter && <span>(从第{cooldown.recent_chapter}章起)</span>}
          </div>
        ) : (
          <div className="gf-cooldown-ready">
            <span className="cooldown-ready-badge">就绪</span>
            <span>随时可用</span>
          </div>
        )}
      </div>

      {/* Activation count */}
      <div className="gf-section">
        <h4>激活次数</h4>
        <p>{gf.activation_count ?? 0} 次</p>
      </div>

      {/* Evolution stages */}
      {gf.evolution_stages && gf.evolution_stages.length > 0 && (
        <div className="gf-section">
          <h4>进化节点</h4>
          <div className="gf-evolution-stages">
            {gf.evolution_stages.map(stage => (
              <span key={stage} className="evolution-node">
                {stage === gf.level ? `★ Lv.${stage}` : `Lv.${stage}`}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── RhythmTab ───
function RhythmTab({ data, loading, error, onRetry }) {
  if (loading) return <div className="query-loading">加载中…</div>
  if (error) return (
    <div className="query-error">
      <p className="error-text">{error}</p>
      <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
    </div>
  )
  if (!data || !data.rhythm_data || Object.keys(data.rhythm_data).length === 0) {
    return <div className="query-empty">暂无节奏数据</div>
  }

  const rhythmData = data.rhythm_data || {}

  return (
    <div className="query-tab-content rhythm-tab">
      <h3>节奏分析</h3>
      {Object.entries(rhythmData).map(([volKey, volData]) => (
        <div key={volKey} className="rhythm-volume-section">
          <h4 className="rhythm-volume-title">{volKey.replace('_', ' ')} ({volData.total_chapters}章)</h4>

          {/* Pacing score */}
          <div className="rhythm-pacing">
            <span className="rhythm-pacing-score">节奏评分: {volData.pacing_score}</span>
            <span className={`pacing-label pacing-${volData.pacing_label === '快节奏' ? 'fast' : volData.pacing_label === '慢节奏' ? 'slow' : 'medium'}`}>
              {volData.pacing_label}
            </span>
          </div>

          {/* Beat distribution (bar chart) */}
          <div className="rhythm-beat-section">
            <h5>节拍分布</h5>
            <div className="rhythm-beat-bars">
              {Object.entries(volData.beat_distribution || {}).map(([beat, count]) => (
                <div key={beat} className="beat-bar-row">
                  <span className="beat-label">{beat}</span>
                  <div className="beat-bar-track">
                    <div className="beat-bar-fill" style={{ width: `${Math.min(count / (volData.total_chapters || 1) * 100, 100)}%` }} />
                  </div>
                  <span className="beat-count">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Emotion curve (SVG line) */}
          {volData.emotion_curve && volData.emotion_curve.length > 0 && (
            <div className="rhythm-emotion-section">
              <h5>情绪曲线 (均值: {volData.avg_emotion_intensity})</h5>
              <EmotionCurveSVG data={volData.emotion_curve} />
            </div>
          )}

          {/* Climax chapters */}
          {volData.climax_chapters && volData.climax_chapters.length > 0 && (
            <div className="rhythm-climax-section">
              <h5>高潮章节</h5>
              <div className="climax-chapters-list">
                {volData.climax_chapters.map(ch => (
                  <span key={ch} className="climax-chapter-badge">第{ch}章</span>
                ))}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// Simple SVG emotion curve
function EmotionCurveSVG({ data }) {
  if (!data || data.length === 0) return null
  const width = 400
  const height = 80
  const padding = 10
  const maxIntensity = Math.max(...data.map(d => d.intensity), 1)
  const xStep = (width - padding * 2) / Math.max(data.length - 1, 1)

  const points = data.map((d, i) => {
    const x = padding + i * xStep
    const y = padding + (1 - d.intensity / maxIntensity) * (height - padding * 2)
    return `${x},${y}`
  })

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="emotion-svg">
      <polyline
        points={points.join(' ')}
        fill="none"
        stroke="var(--accent-purple)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      {data.map((d, i) => {
        const x = padding + i * xStep
        const y = padding + (1 - d.intensity / maxIntensity) * (height - padding * 2)
        return (
          <circle key={i} cx={x} cy={y} r="3" fill="var(--accent-purple)" />
        )
      })}
    </svg>
  )
}

// ─── DebtTab ───
function DebtTab({ data, loading, error, onRetry }) {
  if (loading) return <div className="query-loading">加载中…</div>
  if (error) return (
    <div className="query-error">
      <p className="error-text">{error}</p>
      <button type="button" className="workbench-primary-button" onClick={onRetry}>重新加载</button>
    </div>
  )
  if (!data || !data.debt_summary) return <div className="query-empty">暂无债务数据</div>

  const { debt_summary = {} } = data
  const { total_unresolved = 0, total_resolved = 0, resolution_rate = 0, critical_debts = [], recently_resolved = [] } = debt_summary

  return (
    <div className="query-tab-content debt-tab">
      <h3>债务查询</h3>

      {/* Summary stats */}
      <div className="debt-summary">
        <div className="debt-stat">
          <span className="debt-stat-value">{total_unresolved}</span>
          <span className="debt-stat-label">待偿还</span>
        </div>
        <div className="debt-stat">
          <span className="debt-stat-value">{total_resolved}</span>
          <span className="debt-stat-label">已解决</span>
        </div>
        <div className="debt-stat">
          <span className="debt-stat-value">{resolution_rate}%</span>
          <span className="debt-stat-label">解决率</span>
        </div>
      </div>

      {/* Critical debts */}
      <div className="debt-section">
        <h4>紧急债务 (weight &ge; 4)</h4>
        {critical_debts.length === 0 ? (
          <p className="empty-text">暂无紧急债务</p>
        ) : (
          <div className="critical-debt-list">
            {critical_debts.map(debt => (
              <div key={debt.id} className="critical-debt-item">
                <div className="debt-item-header">
                  <span className="debt-id">{debt.id}</span>
                  <span className="debt-urgency-badge" style={{ color: debt.urgency >= 4 ? 'var(--accent-red)' : 'var(--accent-amber)' }}>
                    紧急度: {debt.urgency}
                  </span>
                </div>
                <div className="debt-meta">
                  <span>埋入: 第{debt.plant_chapter}章</span>
                  <span>预期: 第{debt.expected_payoff_chapter}章</span>
                  {debt.overdue_chapters > 0 && (
                    <span className="overdue-tag">逾期{debt.overdue_chapters}章</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recently resolved */}
      <div className="debt-section">
        <h4>最近已解决</h4>
        {recently_resolved.length === 0 ? (
          <p className="empty-text">暂无已解决债务</p>
        ) : (
          <div className="resolved-debt-list">
            {recently_resolved.map((debt, i) => (
              <div key={debt.id || i} className="resolved-debt-item">
                <span className="debt-id">{debt.id}</span>
                <span className="debt-resolved-chapter">解决于第{debt.payoff_chapter || '?'}章</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
