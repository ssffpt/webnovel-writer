import { useState } from 'react'
import { createProject } from '../api.js'

const DEFAULT_FORM = {
  title: '',
  genres: [],
  target_words: 2000000,
  target_chapters: 600,
  core_selling_points: '',
  protagonist_name: '',
  golden_finger_name: '',
  golden_finger_type: 'none',
}

export default function CreateWizard({ open, onClose, onCreated, genres, goldenFingerTypes, prefillData }) {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({ ...DEFAULT_FORM, ...prefillData })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  if (!open) return null

  function updateField(field, value) {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  function toggleGenre(genreKey) {
    setFormData(prev => {
      const current = prev.genres || []
      const next = current.includes(genreKey)
        ? current.filter(k => k !== genreKey)
        : [...current, genreKey]
      return { ...prev, genres: next }
    })
  }

  function validateStep1() {
    if (!formData.title.trim()) return '书名不能为空'
    if (!formData.genres || formData.genres.length === 0) return '请至少选择一个题材'
    return ''
  }

  function handleNext() {
    if (step === 1) {
      const err = validateStep1()
      if (err) { setError(err); return }
      setError('')
    }
    setStep(prev => Math.min(prev + 1, 3))
  }

  function handleBack() {
    setStep(prev => Math.max(prev - 1, 1))
    setError('')
  }

  function handleSkip() {
    setStep(3)
  }

  async function handleSubmit() {
    setCreating(true)
    setError('')
    try {
      const payload = {
        title: formData.title.trim(),
        genre: formData.genres[0] || '',
        target_words: formData.target_words,
        target_chapters: formData.target_chapters,
        core_selling_points: formData.core_selling_points || undefined,
        protagonist_name: formData.protagonist_name || undefined,
        golden_finger_name: formData.golden_finger_name || undefined,
        golden_finger_type: formData.golden_finger_type || undefined,
      }
      const result = await createProject(payload)
      if (onCreated) onCreated(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败')
    } finally {
      setCreating(false)
    }
  }

  function handleClose() {
    if (creating) return
    setStep(1)
    setFormData({ ...DEFAULT_FORM })
    setError('')
    if (onClose) onClose()
  }

  const selectedGfType = formData.golden_finger_type

  return (
    <div className="create-wizard-overlay" onClick={handleClose}>
      <div className="create-wizard-modal" onClick={e => e.stopPropagation()}>
        {/* Step indicator */}
        <div className="create-wizard-step-indicator">
          <span className={step >= 1 ? 'active' : ''}>1 基本信息</span>
          <span className="create-wizard-step-arrow">→</span>
          <span className={step >= 2 ? 'active' : ''}>2 主角设定</span>
          <span className="create-wizard-step-arrow">→</span>
          <span className={step >= 3 ? 'active' : ''}>3 确认创建</span>
        </div>

        {/* Step 1: 基本信息 */}
        {step === 1 && (
          <div className="create-wizard-content">
            <h2>基本信息</h2>

            <div className="create-wizard-field">
              <label>书名 <span className="required">*</span></label>
              <input
                type="text"
                value={formData.title}
                onChange={e => updateField('title', e.target.value)}
                placeholder="输入你的小说书名"
                className="create-wizard-input"
              />
            </div>

            <div className="create-wizard-field">
              <label>题材 <span className="required">*</span></label>
              <div className="genre-tag-list">
                {(genres || []).map(g => (
                  <button
                    key={g.key}
                    type="button"
                    className={`genre-tag ${formData.genres.includes(g.key) ? 'selected' : ''}`}
                    onClick={() => toggleGenre(g.key)}
                  >
                    {g.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="create-wizard-field-row">
              <div className="create-wizard-field">
                <label>目标字数</label>
                <input
                  type="number"
                  value={formData.target_words}
                  onChange={e => updateField('target_words', Number(e.target.value))}
                  className="create-wizard-input"
                />
              </div>
              <div className="create-wizard-field">
                <label>目标章节数</label>
                <input
                  type="number"
                  value={formData.target_chapters}
                  onChange={e => updateField('target_chapters', Number(e.target.value))}
                  className="create-wizard-input"
                />
              </div>
            </div>

            <div className="create-wizard-field">
              <label>核心卖点（可选）</label>
              <textarea
                value={formData.core_selling_points}
                onChange={e => updateField('core_selling_points', e.target.value)}
                placeholder="描述你小说的核心卖点…"
                className="create-wizard-textarea"
                rows={3}
              />
            </div>

            {error && <p className="error-text">{error}</p>}

            <div className="create-wizard-actions">
              <button type="button" className="workbench-nav-button" onClick={handleClose}>取消</button>
              <button type="button" className="workbench-primary-button" onClick={handleNext}>下一步</button>
            </div>
          </div>
        )}

        {/* Step 2: 主角设定 */}
        {step === 2 && (
          <div className="create-wizard-content">
            <h2>主角设定（可选）</h2>

            <div className="create-wizard-field">
              <label>主角名字</label>
              <input
                type="text"
                value={formData.protagonist_name}
                onChange={e => updateField('protagonist_name', e.target.value)}
                placeholder="输入主角名字"
                className="create-wizard-input"
              />
            </div>

            <div className="create-wizard-field">
              <label>金手指名称</label>
              <input
                type="text"
                value={formData.golden_finger_name}
                onChange={e => updateField('golden_finger_name', e.target.value)}
                placeholder="输入金手指名称"
                className="create-wizard-input"
              />
            </div>

            <div className="create-wizard-field">
              <label>金手指类型</label>
              <div className="gf-type-list">
                {(goldenFingerTypes || []).map(t => (
                  <label
                    key={t.key}
                    className={`gf-option ${t.key === 'none' ? 'none' : ''} ${selectedGfType === t.key ? 'selected' : ''}`}
                  >
                    <input
                      type="radio"
                      name="golden_finger_type"
                      value={t.key}
                      checked={selectedGfType === t.key}
                      onChange={() => updateField('golden_finger_type', t.key)}
                    />
                    <span>{t.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {error && <p className="error-text">{error}</p>}

            <div className="create-wizard-actions">
              <button type="button" className="workbench-nav-button" onClick={handleBack}>上一步</button>
              <button type="button" className="workbench-primary-button" onClick={handleNext}>下一步</button>
              <button type="button" className="create-wizard-skip-link" onClick={handleSkip}>跳过此步→</button>
            </div>
          </div>
        )}

        {/* Step 3: 确认创建 */}
        {step === 3 && (
          <div className="create-wizard-content">
            <h2>确认创建</h2>

            <div className="create-wizard-summary">
              <div className="create-wizard-summary-row">
                <span className="create-wizard-summary-label">书名</span>
                <span className="create-wizard-summary-value">{formData.title}</span>
              </div>
              <div className="create-wizard-summary-row">
                <span className="create-wizard-summary-label">题材</span>
                <span className="create-wizard-summary-value">
                  {(genres || []).filter(g => formData.genres.includes(g.key)).map(g => g.label).join('、') || '未选择'}
                </span>
              </div>
              <div className="create-wizard-summary-row">
                <span className="create-wizard-summary-label">目标字数</span>
                <span className="create-wizard-summary-value">{(formData.target_words / 10000).toFixed(0)}万字</span>
              </div>
              <div className="create-wizard-summary-row">
                <span className="create-wizard-summary-label">目标章节数</span>
                <span className="create-wizard-summary-value">{formData.target_chapters}章</span>
              </div>
              {formData.core_selling_points && (
                <div className="create-wizard-summary-row">
                  <span className="create-wizard-summary-label">核心卖点</span>
                  <span className="create-wizard-summary-value">{formData.core_selling_points}</span>
                </div>
              )}
              {formData.protagonist_name && (
                <div className="create-wizard-summary-row">
                  <span className="create-wizard-summary-label">主角</span>
                  <span className="create-wizard-summary-value">{formData.protagonist_name}</span>
                </div>
              )}
              {formData.golden_finger_name && (
                <div className="create-wizard-summary-row">
                  <span className="create-wizard-summary-label">金手指</span>
                  <span className="create-wizard-summary-value">
                    {formData.golden_finger_name}
                    {formData.golden_finger_type && formData.golden_finger_type !== 'none' && (
                      <span className="chapter-file-meta">（{(goldenFingerTypes || []).find(t => t.key === formData.golden_finger_type)?.label || formData.golden_finger_type}）</span>
                    )}
                  </span>
                </div>
              )}
            </div>

            {error && <p className="error-text">{error}</p>}

            <div className="create-wizard-actions">
              <button type="button" className="workbench-nav-button" onClick={handleBack} disabled={creating}>上一步</button>
              <button type="button" className="workbench-primary-button" onClick={handleSubmit} disabled={creating}>
                {creating ? '创建中…' : '创建项目'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
