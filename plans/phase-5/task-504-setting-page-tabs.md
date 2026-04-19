# Task 504: SettingPage 标签页扩展

## 目标

扩展 SettingPage，新增伏笔/金手指/节奏/债务四个标签页。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/SettingPage.jsx`（修改）
- `webnovel-writer/dashboard/frontend/src/api.js`（修改，新增查询 API 函数）

## 依赖

- task-503（后端 4 个查询 API 已实现）

## 前置知识

SettingPage 当前结构：实体列表 + 实体详情（从 index.db 查询）。

api.js 中需要新增的函数：

```javascript
export async function queryForeshadowing(projectRoot) {
  const res = await fetch(`/api/query/foreshadowing?project_root=${encodeURIComponent(projectRoot)}`)
  return res.json()
}

export async function queryRhythm(projectRoot) {
  const res = await fetch(`/api/query/rhythm?project_root=${encodeURIComponent(projectRoot)}`)
  return res.json()
}

export async function queryGoldenFinger(projectRoot) {
  const res = await fetch(`/api/query/golden-finger?project_root=${encodeURIComponent(projectRoot)}`)
  return res.json()
}

export async function queryDebts(projectRoot) {
  const res = await fetch(`/api/query/debts?project_root=${encodeURIComponent(projectRoot)}`)
  return res.json()
}
```

## 规格

### SettingPage 标签页结构

```jsx
import { useState, useEffect } from 'react'
import { queryForeshadowing, queryRhythm, queryGoldenFinger, queryDebts } from '../api'

export default function SettingPage({ projectRoot }) {
  const [activeTab, setActiveTab] = useState('entities')

  const tabs = [
    { id: 'entities', label: '实体' },
    { id: 'foreshadowing', label: '伏笔' },
    { id: 'golden_finger', label: '金手指' },
    { id: 'rhythm', label: '节奏' },
    { id: 'debts', label: '债务' },
  ]

  return (
    <div className="setting-page">
      <div className="tab-bar">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'entities' && <EntityTab projectRoot={projectRoot} />}
        {activeTab === 'foreshadowing' && <ForeshadowingTab projectRoot={projectRoot} />}
        {activeTab === 'golden_finger' && <GoldenFingerTab projectRoot={projectRoot} />}
        {activeTab === 'rhythm' && <RhythmTab projectRoot={projectRoot} />}
        {activeTab === 'debts' && <DebtTab projectRoot={projectRoot} />}
      </div>
    </div>
  )
}
```

### ForeshadowingTab（伏笔标签页）

```jsx
function ForeshadowingTab({ projectRoot }) {
  const [data, setData] = useState(null)
  const [tierFilter, setTierFilter] = useState('all')

  useEffect(() => {
    queryForeshadowing(projectRoot).then(setData)
  }, [projectRoot])

  if (!data) return <p>加载中...</p>

  const { stats, by_tier, foreshadowing } = data
  const filtered = tierFilter === 'all'
    ? foreshadowing
    : by_tier[tierFilter] || []

  return (
    <div className="foreshadowing-tab">
      {/* 统计卡片 */}
      <div className="stats-row">
        <div className="stat-card">总计 {stats.total}</div>
        <div className="stat-card">已埋设 {stats.planted}</div>
        <div className="stat-card">已揭示 {stats.revealed}</div>
        <div className="stat-card stat-warning">超期 {stats.overdue}</div>
        <div className="stat-card">回收率 {(stats.recovery_rate * 100).toFixed(0)}%</div>
      </div>

      {/* 三层分类筛选 */}
      <div className="tier-filter">
        <button className={tierFilter === 'all' ? 'active' : ''} onClick={() => setTierFilter('all')}>全部</button>
        <button className={tierFilter === 'chapter' ? 'active' : ''} onClick={() => setTierFilter('chapter')}>章级</button>
        <button className={tierFilter === 'volume' ? 'active' : ''} onClick={() => setTierFilter('volume')}>卷级</button>
        <button className={tierFilter === 'book' ? 'active' : ''} onClick={() => setTierFilter('book')}>全书</button>
      </div>

      {/* 伏笔列表 */}
      <div className="foreshadowing-list">
        {filtered.map(f => (
          <div key={f.id} className={`foreshadow-card urgency-${f.urgency_level}`}>
            <div className="card-header">
              <span className={`urgency-badge ${f.urgency_level}`}>{f.urgency_level}</span>
              <span className="tier-badge">{f.tier === 'chapter' ? '章级' : f.tier === 'volume' ? '卷级' : '全书'}</span>
            </div>
            <p className="description">{f.description}</p>
            <div className="card-meta">
              <span>埋设：第{f.plant_chapter}章</span>
              <span>预期揭示：第{f.reveal_chapter}章</span>
              <span>剩余：{f.chapters_remaining}章</span>
              <span>紧急度：{(f.urgency * 100).toFixed(0)}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

### GoldenFingerTab（金手指标签页）

```jsx
function GoldenFingerTab({ projectRoot }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    queryGoldenFinger(projectRoot).then(setData)
  }, [projectRoot])

  if (!data) return <p>加载中...</p>

  const { golden_finger: gf, history } = data

  return (
    <div className="golden-finger-tab">
      <div className="gf-header">
        <h3>{gf.name || '未设置金手指'}</h3>
        <span className="gf-type">{gf.type}</span>
      </div>

      <div className="gf-info-grid">
        <div className="info-item"><label>当前等级</label><span>{gf.current_level || '-'}</span></div>
        <div className="info-item"><label>成长节奏</label><span>{gf.growth_style || '-'}</span></div>
        <div className="info-item"><label>可见度</label><span>{gf.visibility || '-'}</span></div>
        <div className="info-item"><label>代价</label><span>{gf.cost || '无'}</span></div>
      </div>

      {gf.skills?.length > 0 && (
        <div className="gf-skills">
          <h4>技能列表</h4>
          <ul>{gf.skills.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}

      {gf.upgrade_conditions?.length > 0 && (
        <div className="gf-upgrade">
          <h4>升级条件</h4>
          <ul>{gf.upgrade_conditions.map((c, i) => <li key={i}>{c}</li>)}</ul>
        </div>
      )}

      {gf.development_suggestions?.length > 0 && (
        <div className="gf-suggestions">
          <h4>发展建议</h4>
          <ul>{gf.development_suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
    </div>
  )
}
```

### RhythmTab（节奏标签页）

```jsx
function RhythmTab({ projectRoot }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    queryRhythm(projectRoot).then(setData)
  }, [projectRoot])

  if (!data) return <p>加载中...</p>

  const { strands, warnings } = data

  return (
    <div className="rhythm-tab">
      {/* 警告 */}
      {warnings.length > 0 && (
        <div className="rhythm-warnings">
          {warnings.map((w, i) => (
            <div key={i} className={`warning-card severity-${w.severity}`}>
              {w.message}
            </div>
          ))}
        </div>
      )}

      {/* Strand 列表 */}
      <div className="strand-list">
        {strands.map(s => (
          <div key={s.name} className={`strand-card status-${s.status}`}>
            <div className="strand-header">
              <span className="strand-name">{s.name}</span>
              <span className={`status-badge ${s.status}`}>{s.status}</span>
              <span>{s.total_chapters} 章</span>
            </div>
            {/* 简化时间轴：章节分布条 */}
            <div className="strand-timeline">
              {s.chapters.map(ch => (
                <span key={ch} className="chapter-dot" title={`第${ch}章`} />
              ))}
            </div>
            {s.gaps.length > 0 && (
              <div className="strand-gaps">
                {s.gaps.filter(g => g.length > 2).map((g, i) => (
                  <span key={i} className="gap-badge">
                    第{g.start}-{g.end}章断档{g.length}章
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

### DebtTab（债务标签页）

```jsx
function DebtTab({ projectRoot }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    queryDebts(projectRoot).then(setData)
  }, [projectRoot])

  if (!data) return <p>加载中...</p>

  const { debts, stats } = data

  return (
    <div className="debt-tab">
      <div className="stats-row">
        <div className="stat-card stat-warning">总债务 {stats.total_debts}</div>
        <div className="stat-card stat-critical">严重 {stats.critical_debts}</div>
        <div className="stat-card">平均超期 {stats.avg_overdue} 章</div>
      </div>

      {debts.length === 0 ? (
        <p className="no-debts">暂无伏笔债务</p>
      ) : (
        <div className="debt-list">
          {debts.map(d => (
            <div key={d.id} className={`debt-card urgency-${d.urgency_level}`}>
              <div className="debt-header">
                <span className={`urgency-badge ${d.urgency_level}`}>{d.urgency_level}</span>
                <span className="overdue">超期 {d.overdue_by} 章</span>
              </div>
              <p className="description">{d.description}</p>
              <p className="suggested-action">{d.suggested_action}</p>
              <div className="debt-meta">
                <span>埋设：第{d.plant_chapter}章</span>
                <span>预期揭示：第{d.reveal_chapter}章</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
```

### EntityTab（保留原有功能）

```jsx
function EntityTab({ projectRoot }) {
  // 保留 SettingPage 原有的实体列表功能
  // 将原有的实体列表代码移入此组件
  // ... 原有代码不变 ...
}
```

## TDD 验收

- Happy path：SettingPage 显示 5 个标签页 → 切换到伏笔 → 显示三层分类 + 紧急度颜色
- Edge case 1：金手指未设置 → 显示"未设置金手指"
- Edge case 2：无债务 → 债务标签页显示"暂无伏笔债务"
- Error case：API 返回错误 → 标签页显示加载失败提示
