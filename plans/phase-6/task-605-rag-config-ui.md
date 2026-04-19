# Task 605: 前端 RAG 配置 + 索引管理 UI

## 目标

实现前端 RAG 配置页面和索引管理 UI，嵌入 OverviewPage 的设置区域。

## 涉及文件

- `webnovel-writer/dashboard/frontend/src/workbench/RAGConfig.jsx`（新建）
- `webnovel-writer/dashboard/frontend/src/workbench/OverviewPage.jsx`（修改，嵌入 RAG 配置）

## 依赖

- task-604（后端 RAG 全部 API 已实现）

## 前置知识

api.js 中需要新增的函数：

```javascript
export async function getRAGConfig(projectRoot) {
  const res = await fetch(`/api/rag/config?project_root=${encodeURIComponent(projectRoot)}`)
  return res.json()
}

export async function saveRAGConfig(projectRoot, config) {
  const res = await fetch(`/api/rag/config?project_root=${encodeURIComponent(projectRoot)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  return res.json()
}

export async function testRAGConnection(projectRoot) {
  const res = await fetch(`/api/rag/test?project_root=${encodeURIComponent(projectRoot)}`, {
    method: 'POST',
  })
  return res.json()
}

export async function startRAGBuild(projectRoot) {
  const res = await fetch(`/api/rag/build?project_root=${encodeURIComponent(projectRoot)}`, {
    method: 'POST',
  })
  return res.json()
}

export async function getRAGBuildStatus(projectRoot, taskId) {
  const url = taskId
    ? `/api/rag/build/status?project_root=${encodeURIComponent(projectRoot)}&task_id=${taskId}`
    : `/api/rag/build/status?project_root=${encodeURIComponent(projectRoot)}`
  const res = await fetch(url)
  return res.json()
}
```

## 规格

### RAGConfig 组件

```jsx
import { useState, useEffect } from 'react'
import {
  getRAGConfig, saveRAGConfig, testRAGConnection,
  startRAGBuild, getRAGBuildStatus,
} from '../api'

/**
 * RAG 配置 + 索引管理面板。
 *
 * Props:
 *   projectRoot: string
 */
export default function RAGConfig({ projectRoot }) {
  const [config, setConfig] = useState(null)
  const [formData, setFormData] = useState({
    embedding_model: '',
    embedding_api_key: '',
    embedding_base_url: '',
    rerank_model: '',
    rerank_api_key: '',
    rerank_base_url: '',
  })
  const [testResult, setTestResult] = useState(null)
  const [buildStatus, setBuildStatus] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getRAGConfig(projectRoot).then(data => {
      setConfig(data)
      setFormData(prev => ({
        ...prev,
        embedding_model: data.embedding?.model || '',
        embedding_base_url: data.embedding?.base_url || '',
        rerank_model: data.rerank?.model || '',
        rerank_base_url: data.rerank?.base_url || '',
      }))
    })
  }, [projectRoot])

  const handleSave = async () => {
    setSaving(true)
    await saveRAGConfig(projectRoot, formData)
    const updated = await getRAGConfig(projectRoot)
    setConfig(updated)
    setSaving(false)
  }

  const handleTest = async () => {
    setTestResult({ testing: true })
    const result = await testRAGConnection(projectRoot)
    setTestResult(result)
  }

  const handleBuild = async () => {
    const result = await startRAGBuild(projectRoot)
    if (result.task_id) {
      setBuildStatus({ status: 'running', progress: 0, message: '开始构建...' })
      pollBuildStatus(result.task_id)
    } else {
      setBuildStatus({ status: 'error', message: result.message })
    }
  }

  const pollBuildStatus = async (taskId) => {
    const check = async () => {
      const status = await getRAGBuildStatus(projectRoot, taskId)
      setBuildStatus(status)
      if (status.status === 'running') {
        setTimeout(check, 2000)
      } else {
        // 刷新配置（更新索引状态）
        const updated = await getRAGConfig(projectRoot)
        setConfig(updated)
      }
    }
    check()
  }

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (!config) return <p>加载中...</p>

  return (
    <div className="rag-config">
      <h3>RAG 向量检索配置</h3>

      {/* 状态指示 */}
      <div className={`rag-status ${config.configured ? 'configured' : 'not-configured'}`}>
        {config.configured ? '已配置' : '未配置'}
        {config.index_status?.exists && ` | 索引：${config.index_status.doc_count} 文档`}
      </div>

      {/* Embedding 配置 */}
      <fieldset>
        <legend>Embedding 模型</legend>
        <div className="form-group">
          <label>模型名称</label>
          <input
            type="text"
            value={formData.embedding_model}
            onChange={e => handleChange('embedding_model', e.target.value)}
            placeholder="text-embedding-3-small"
          />
        </div>
        <div className="form-group">
          <label>API Key</label>
          <input
            type="password"
            value={formData.embedding_api_key}
            onChange={e => handleChange('embedding_api_key', e.target.value)}
            placeholder={config.embedding?.has_api_key ? '已设置（留空不修改）' : '输入 API Key'}
          />
        </div>
        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            value={formData.embedding_base_url}
            onChange={e => handleChange('embedding_base_url', e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
        </div>
      </fieldset>

      {/* Rerank 配置（可选） */}
      <fieldset>
        <legend>Rerank 模型（可选）</legend>
        <div className="form-group">
          <label>模型名称</label>
          <input
            type="text"
            value={formData.rerank_model}
            onChange={e => handleChange('rerank_model', e.target.value)}
            placeholder="rerank-v3（可选）"
          />
        </div>
        <div className="form-group">
          <label>API Key</label>
          <input
            type="password"
            value={formData.rerank_api_key}
            onChange={e => handleChange('rerank_api_key', e.target.value)}
            placeholder={config.rerank?.has_api_key ? '已设置' : '输入 API Key（可选）'}
          />
        </div>
        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            value={formData.rerank_base_url}
            onChange={e => handleChange('rerank_base_url', e.target.value)}
            placeholder="https://api.cohere.ai/v1（可选）"
          />
        </div>
      </fieldset>

      {/* 操作按钮 */}
      <div className="rag-actions">
        <button className="btn-primary" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存配置'}
        </button>
        <button className="btn-secondary" onClick={handleTest} disabled={!config.configured}>
          测试连接
        </button>
      </div>

      {/* 测试结果 */}
      {testResult && !testResult.testing && (
        <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
          {testResult.message}
          {testResult.latency_ms && ` (${testResult.latency_ms}ms)`}
        </div>
      )}

      {/* 索引管理 */}
      <div className="index-management">
        <h4>向量索引</h4>
        {config.index_status?.exists ? (
          <div className="index-info">
            <p>文档数：{config.index_status.doc_count}</p>
            <p>构建时间：{config.index_status.last_built || '-'}</p>
          </div>
        ) : (
          <p>尚未构建索引</p>
        )}

        <button
          className="btn-primary"
          onClick={handleBuild}
          disabled={!config.configured || buildStatus?.status === 'running'}
        >
          {config.index_status?.exists ? '重建索引' : '构建索引'}
        </button>

        {/* 构建进度 */}
        {buildStatus?.status === 'running' && (
          <div className="build-progress">
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${(buildStatus.progress || 0) * 100}%` }} />
            </div>
            <p>{buildStatus.message}</p>
          </div>
        )}

        {buildStatus?.status === 'completed' && (
          <p className="build-success">{buildStatus.message}</p>
        )}

        {buildStatus?.status === 'failed' && (
          <p className="build-error">{buildStatus.message}</p>
        )}
      </div>
    </div>
  )
}
```

### OverviewPage 集成

```jsx
import RAGConfig from './RAGConfig'

// 在 OverviewPage 中，设置区域新增 RAG 配置
function SettingsSection({ projectRoot }) {
  const [showRAG, setShowRAG] = useState(false)

  return (
    <div className="settings-section">
      <h3>项目设置</h3>

      {/* Git 自动提交开关（已有） */}
      <GitAutoCommitToggle projectRoot={projectRoot} />

      {/* RAG 配置 */}
      <div className="setting-item">
        <button onClick={() => setShowRAG(!showRAG)}>
          RAG 向量检索 {showRAG ? '▼' : '▶'}
        </button>
        {showRAG && <RAGConfig projectRoot={projectRoot} />}
      </div>
    </div>
  )
}
```

## TDD 验收

- Happy path：填写 Embedding 配置 → 保存 → 测试连接成功 → 构建索引 → 进度条递增 → 完成
- Edge case 1：未配置时"测试连接"和"构建索引"按钮禁用
- Edge case 2：已有索引 → 按钮文字变为"重建索引"
- Error case：测试连接失败 → 显示红色错误信息
