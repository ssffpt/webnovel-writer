import { useState, useEffect, useCallback } from 'react'
import {
  getRAGConfig, saveRAGConfig, testRAGConnection,
  startRAGBuild, getRAGBuildStatus,
} from '../api.js'

/**
 * RAG 配置 + 索引管理面板。
 */
export default function RAGConfig() {
  const [config, setConfig] = useState(null)
  const [formData, setFormData] = useState({
    RAG_EMBEDDING_MODEL: '',
    RAG_EMBEDDING_API_KEY: '',
    RAG_EMBEDDING_BASE_URL: '',
    RAG_RERANK_MODEL: '',
    RAG_RERANK_API_KEY: '',
    RAG_RERANK_BASE_URL: '',
  })
  const [testResult, setTestResult] = useState(null)
  const [buildStatus, setBuildStatus] = useState(null)
  const [saving, setSaving] = useState(false)

  const loadConfig = useCallback(async () => {
    try {
      const data = await getRAGConfig()
      setConfig(data)
      setFormData(prev => ({
        ...prev,
        RAG_EMBEDDING_MODEL: data.embedding_model || '',
        RAG_RERANK_MODEL: data.rerank_model || '',
      }))
    } catch {
      setConfig({ enabled: false, embedding_model: '', has_api_key: false })
    }
  }, [])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  const handleSave = async () => {
    setSaving(true)
    try {
      await saveRAGConfig(formData)
      await loadConfig()
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTestResult({ testing: true })
    try {
      const result = await testRAGConnection()
      setTestResult(result)
    } catch (err) {
      setTestResult({ success: false, message: err.message })
    }
  }

  const handleBuild = async () => {
    try {
      const result = await startRAGBuild()
      if (result.task_id) {
        setBuildStatus({ status: 'running', progress: 0, message: '开始构建...' })
        pollBuildStatus(result.task_id)
      } else {
        setBuildStatus({ status: 'error', message: result.message || '构建失败' })
      }
    } catch (err) {
      setBuildStatus({ status: 'error', message: err.message })
    }
  }

  const pollBuildStatus = async (taskId) => {
    const check = async () => {
      try {
        const status = await getRAGBuildStatus(taskId)
        setBuildStatus(status)
        if (status.status === 'running') {
          setTimeout(check, 2000)
        } else {
          await loadConfig()
        }
      } catch {
        // 忽略轮询错误
      }
    }
    check()
  }

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (!config) return <p>加载中...</p>

  const isConfigured = config.has_api_key || config.enabled

  return (
    <div className="rag-config">
      <h3>RAG 向量检索配置</h3>

      {/* 状态指示 */}
      <div className={`rag-status ${isConfigured ? 'configured' : 'not-configured'}`}>
        {isConfigured ? '已配置' : '未配置'}
      </div>

      {/* Embedding 配置 */}
      <fieldset className="rag-fieldset">
        <legend>Embedding 模型</legend>
        <div className="form-group">
          <label>模型名称</label>
          <input
            type="text"
            value={formData.RAG_EMBEDDING_MODEL}
            onChange={e => handleChange('RAG_EMBEDDING_MODEL', e.target.value)}
            placeholder="text-embedding-3-small"
          />
        </div>
        <div className="form-group">
          <label>API Key</label>
          <input
            type="password"
            value={formData.RAG_EMBEDDING_API_KEY}
            onChange={e => handleChange('RAG_EMBEDDING_API_KEY', e.target.value)}
            placeholder={config.has_api_key ? '已设置（留空不修改）' : '输入 API Key'}
          />
        </div>
        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            value={formData.RAG_EMBEDDING_BASE_URL}
            onChange={e => handleChange('RAG_EMBEDDING_BASE_URL', e.target.value)}
            placeholder="https://api.openai.com/v1"
          />
        </div>
      </fieldset>

      {/* Rerank 配置（可选） */}
      <fieldset className="rag-fieldset">
        <legend>Rerank 模型（可选）</legend>
        <div className="form-group">
          <label>模型名称</label>
          <input
            type="text"
            value={formData.RAG_RERANK_MODEL}
            onChange={e => handleChange('RAG_RERANK_MODEL', e.target.value)}
            placeholder="rerank-v3（可选）"
          />
        </div>
        <div className="form-group">
          <label>API Key</label>
          <input
            type="password"
            value={formData.RAG_RERANK_API_KEY}
            onChange={e => handleChange('RAG_RERANK_API_KEY', e.target.value)}
            placeholder="输入 API Key（可选）"
          />
        </div>
        <div className="form-group">
          <label>Base URL</label>
          <input
            type="text"
            value={formData.RAG_RERANK_BASE_URL}
            onChange={e => handleChange('RAG_RERANK_BASE_URL', e.target.value)}
            placeholder="https://api.cohere.ai/v1（可选）"
          />
        </div>
      </fieldset>

      {/* 操作按钮 */}
      <div className="rag-actions">
        <button className="workbench-primary-button" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存配置'}
        </button>
        <button className="workbench-nav-button" onClick={handleTest} disabled={!isConfigured}>
          测试连接
        </button>
      </div>

      {/* 测试结果 */}
      {testResult && !testResult.testing && (
        <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
          {testResult.success ? '连接成功' : `连接失败：${testResult.message || '未知错误'}`}
        </div>
      )}

      {/* 索引管理 */}
      <div className="index-management">
        <h4>向量索引</h4>

        <button
          className="workbench-primary-button"
          onClick={handleBuild}
          disabled={!isConfigured || buildStatus?.status === 'running'}
        >
          {buildStatus?.status === 'running' ? '构建中...' : '构建索引'}
        </button>

        {/* 构建进度 */}
        {buildStatus?.status === 'running' && (
          <div className="build-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${(buildStatus.progress || 0) * 100}%` }}
              />
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
