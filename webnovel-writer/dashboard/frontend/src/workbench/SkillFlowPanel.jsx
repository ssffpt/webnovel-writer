import { useCallback, useEffect, useRef, useState } from 'react'
import { getSkillStatus, submitSkillStep, cancelSkill, goBackSkill } from '../api.js'

// --- Step Progress Bar ---

function StepIndicator({ steps, onStepClick }) {
  return (
    <div className="skill-flow-step-bar">
      {steps.map((step, i) => {
        const isCompleted = step.status === 'completed'
        const isClickable = isCompleted && onStepClick
        return (
          <div
            key={step.id}
            className={`skill-flow-step-item ${step.status === 'completed' ? 'completed' : ''} ${step.status === 'running' ? 'running' : ''} ${isClickable ? 'clickable' : ''}`}
            onClick={isClickable ? () => onStepClick(step.id) : undefined}
            role={isClickable ? 'button' : undefined}
            tabIndex={isClickable ? 0 : undefined}
          >
            <span className="skill-flow-step-marker">
              {step.status === 'completed' ? '\u2713' : step.status === 'running' ? '\u25CF' : '\u25CB'}
            </span>
            <span className="skill-flow-step-label">{step.name}</span>
            {i < steps.length - 1 && <span className="skill-flow-step-connector" />}
          </div>
        )
      })}
    </div>
  )
}

// --- Log Stream ---

function LogStream({ logs }) {
  const bottomRef = useRef(null)
  const prevLengthRef = useRef(0)

  useEffect(() => {
    if (logs.length > prevLengthRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
    prevLengthRef.current = logs.length
  }, [logs.length])

  return (
    <div className="skill-flow-logs">
      {logs.map((log, i) => (
        <div key={i} className="skill-flow-log-item">
          {log.message || String(log)}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}

// --- Auto Step Panel ---

function AutoStepPanel({ step }) {
  return (
    <div className="skill-flow-step-panel skill-flow-step-panel--auto">
      <div className="skill-flow-spinner-row">
        <span className="loading-spinner" />
        <span className="skill-flow-step-status-text">
          {step.status === 'running' ? '\u6b63\u5728\u6267\u884c...' : '\u7b49\u5f85\u4e2d...'}
        </span>
      </div>
    </div>
  )
}

// --- Form Step Panel ---

function FormStepPanel({ step, onSubmit, onGoBack, canGoBack }) {
  const [formData, setFormData] = useState(() => {
    // 回显已提交的数据（从 input_data 恢复）
    const saved = step.input_data ?? {}
    return { ...saved }
  })
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const schema = step.schema ?? step.output_data?.schema ?? {}

  function handleChange(field, value) {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  function handleMultiSelectToggle(field, option) {
    setFormData(prev => {
      const current = prev[field] ?? []
      const next = current.includes(option)
        ? current.filter(v => v !== option)
        : [...current, option]
      return { ...prev, [field]: next }
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    setSubmitting(true)
    try {
      await onSubmit(step.id, formData)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const fields = schema.fields ?? []
  const isLastStep = false // 将由父组件传入

  function isFieldHidden(field) {
    if (!field.hide_when) return false
    return Object.entries(field.hide_when).every(([key, val]) => formData[key] === val)
  }

  return (
    <div className="skill-flow-step-panel skill-flow-step-panel--form">
      <h4 className="skill-flow-step-title">{step.name || step.id}</h4>
      <form onSubmit={handleSubmit} className="skill-flow-form">
        {fields.length === 0 && (
          <p className="skill-flow-no-fields">该步骤没有表单字段</p>
        )}
        {fields.filter(f => !isFieldHidden(f)).map(field => (
          <div key={field.name} className="skill-flow-form-field">
            <label className="skill-flow-form-label">
              {field.label || field.name}
              {field.required && <span className="required"> *</span>}
            </label>
            {field.type === 'textarea' ? (
              <textarea
                className="skill-flow-form-textarea"
                value={formData[field.name] ?? ''}
                onChange={e => handleChange(field.name, e.target.value)}
                placeholder={field.hint || field.placeholder}
                required={field.required}
                rows={4}
              />
            ) : field.type === 'select' ? (
              <select
                className="skill-flow-form-select"
                value={formData[field.name] ?? ''}
                onChange={e => handleChange(field.name, e.target.value)}
                required={field.required}
              >
                <option value="">请选择</option>
                {(field.options ?? []).map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : field.type === 'multi_select' ? (
              <div className="skill-flow-form-multi-select">
                {(field.options ?? []).map(opt => {
                  const selected = (formData[field.name] ?? []).includes(opt)
                  return (
                    <button
                      key={opt}
                      type="button"
                      className={`skill-flow-tag ${selected ? 'skill-flow-tag--selected' : ''}`}
                      onClick={() => handleMultiSelectToggle(field.name, opt)}
                    >
                      {opt}
                    </button>
                  )
                })}
                {(formData[field.name] ?? []).length === 0 && (
                  <span className="skill-flow-form-hint">{field.hint || '点击选择'}</span>
                )}
              </div>
            ) : field.type === 'number' ? (
              <input
                type="number"
                className="skill-flow-form-input"
                value={formData[field.name] ?? field.default ?? ''}
                onChange={e => handleChange(field.name, e.target.value ? Number(e.target.value) : '')}
                placeholder={field.hint || field.placeholder}
                required={field.required}
              />
            ) : (
              <input
                type={field.type || 'text'}
                className="skill-flow-form-input"
                value={formData[field.name] ?? ''}
                onChange={e => handleChange(field.name, e.target.value)}
                placeholder={field.hint || field.placeholder}
                required={field.required}
              />
            )}
            {field.hint && field.type !== 'multi_select' && (
              <span className="skill-flow-form-hint">{field.hint}</span>
            )}
          </div>
        ))}
        {formError && <p className="error-text">{formError}</p>}
        <div className="skill-flow-form-actions">
          {canGoBack && (
            <button
              type="button"
              className="workbench-primary-button workbench-primary-button--secondary"
              onClick={onGoBack}
              disabled={submitting}
            >
              上一步
            </button>
          )}
          <button
            type="submit"
            className="workbench-primary-button"
            disabled={submitting}
          >
            {submitting ? '提交中...' : '下一步'}
          </button>
        </div>
      </form>
    </div>
  )
}

// --- Confirm Step Panel ---

function ConfirmStepPanel({ step, onConfirm, onCancel, confirming }) {
  const packages = step.output_data?.packages ?? []
  const hasPackages = packages.length > 0
  // Auto-select when there's only one package
  const [selectedPkgId, setSelectedPkgId] = useState(() =>
    packages.length === 1 ? packages[0].id : null
  )

  return (
    <div className="skill-flow-step-panel skill-flow-step-panel--confirm">
      <h4 className="skill-flow-step-title">{step.name || step.id}</h4>
      {step.output_data?.instruction && (
        <p className="skill-flow-confirm-message">{step.output_data.instruction}</p>
      )}
      {hasPackages && (
        <div className="skill-flow-packages">
          {packages.map(pkg => (
            <div
              key={pkg.id}
              className={`skill-flow-package-card ${selectedPkgId === pkg.id ? 'skill-flow-package-card--selected' : ''}`}
              onClick={() => setSelectedPkgId(pkg.id)}
              style={{ cursor: 'pointer' }}
            >
              <div className="skill-flow-package-select-row">
                <span className={`skill-flow-radio ${selectedPkgId === pkg.id ? 'skill-flow-radio--checked' : ''}`} />
                <h4>{pkg.name}</h4>
              </div>
              <p>{pkg.description}</p>
              {pkg.constraints && (
                <ul className="skill-flow-constraints">
                  {pkg.constraints.map((c, i) => (
                    <li key={i}><strong>{c.type}</strong>: {c.content}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
      {step.output_data?.summary && (
        <pre className="skill-flow-confirm-result">{step.output_data.summary}</pre>
      )}
      {step.output_data?.message && !step.output_data?.summary && !hasPackages && (
        <p className="skill-flow-confirm-message">{step.output_data.message}</p>
      )}
      {step.output_data?.result != null && !step.output_data?.summary && (
        <pre className="skill-flow-confirm-result">
          {typeof step.output_data.result === 'object'
            ? JSON.stringify(step.output_data.result, null, 2)
            : String(step.output_data.result)}
        </pre>
      )}
      {step.output_data?.missing?.length > 0 && (
        <div className="gate-warning">
          <p>以下必填项缺失：{step.output_data.missing.join('、')}</p>
        </div>
      )}
      <div className="skill-flow-confirm-actions">
        <button
          type="button"
          className="workbench-primary-button workbench-primary-button--secondary"
          onClick={onCancel}
          disabled={confirming}
        >
          返回
        </button>
        <button
          type="button"
          className="workbench-primary-button"
          onClick={() => onConfirm({ confirmed: true, selected_package_id: selectedPkgId || (hasPackages ? undefined : 'pkg_fallback') })}
          disabled={confirming || (hasPackages && !selectedPkgId)}
        >
          {confirming ? '处理中...' : '确认'}
        </button>
      </div>
    </div>
  )
}

// --- Error Panel ---

function ErrorPanel({ error }) {
  return (
    <div className="skill-flow-error-panel">
      <h4 className="skill-flow-error-title">\u6267\u884c\u9519\u8bef</h4>
      <p className="error-text">{error}</p>
    </div>
  )
}

// --- Cancelled Panel ---

function CancelledPanel() {
  return (
    <div className="skill-flow-cancelled-panel">
      <p className="skill-flow-cancelled-text">\u6d41\u7a0b\u5df2\u53d6\u6d88</p>
    </div>
  )
}

// --- Completed Panel ---

function CompletedPanel({ result }) {
  return (
    <div className="skill-flow-completed-panel">
      <div className="skill-flow-completed-icon">&#10003;</div>
      <h4 className="skill-flow-completed-title">\u5b8c\u6210</h4>
      {result && (
        <pre className="skill-flow-completed-result">
          {typeof result === 'object'
            ? JSON.stringify(result, null, 2)
            : String(result)}
        </pre>
      )}
    </div>
  )
}

// --- Helpers ---

function normalizeStepStatus(status) {
  if (status === 'running') return 'running'
  if (status === 'waiting_input') return 'waiting_input'
  if (status === 'done' || status === 'completed') return 'completed'
  return 'pending'
}

/**
 * Merge steps (StepDefinition[]) and step_states (StepState[]) into
 * a unified step list with both definition (id, name, interaction) and
 * runtime state (status, output_data, progress).
 */
function mergeStepsAndStates(steps, stepStates) {
  const stateMap = {}
  for (const ss of stepStates) {
    const key = ss.step_id ?? ss.id
    stateMap[key] = ss
  }

  return steps.map(def => {
    const state = stateMap[def.id ?? def.step_id]
    return {
      id: def.id ?? def.step_id,
      name: def.name ?? def.step_id,
      interaction: def.interaction,
      schema: def.schema ?? null,
      status: state ? normalizeStepStatus(state.status) : 'pending',
      output_data: state?.output_data ?? null,
      input_data: state?.input_data ?? null,
      progress: state?.progress ?? 0,
    }
  })
}

function inferMode(step) {
  if (step.interaction) return step.interaction
  if (step.status === 'waiting_input') return 'confirm'
  return 'auto'
}

// --- Main SkillFlowPanel ---

/**
 * @param {string} skillId - Active skill instance ID
 * @param {object} stepRenderers - Optional custom step UI components keyed by step id
 * @param {(finalState?: object) => void} onCompleted - Called when skill completes
 * @param {() => void} onCancelled - Called when skill is cancelled
 */
export default function SkillFlowPanel({ skillId, stepRenderers, onCompleted, onCancelled }) {
  const [state, setState] = useState(() => ({
    status: 'loading', // loading|active|completed|failed|cancelled
    skillName: '',
    steps: [],
    currentStep: null,
    logs: [],
    result: null,
    error: null,
  }))
  const [confirming, setConfirming] = useState(false)
  const pollIntervalRef = useRef(null)
  const notifiedRef = useRef(false) // prevent duplicate onCompleted/onCancelled

  // Build the current step object from the unified steps list + SSE update
  function buildCurrentStep(steps, eventStep) {
    // If SSE provides a running/waiting step, find it in the unified list
    const stepId = eventStep?.step_id ?? eventStep?.id
    if (stepId && (eventStep.status === 'running' || eventStep.status === 'waiting_input')) {
      const base = steps.find(s => s.id === stepId)
      return base ? { ...base, ...normalizeEventStep(eventStep) } : null
    }
    // Otherwise, find the first running/waiting step
    return steps.find(s => s.status === 'running' || s.status === 'waiting_input') || null
  }

  const handleSkillEvent = useCallback((event) => {
    if (!event?.skillId || event.skillId !== skillId) return

    switch (event.type) {
      case 'skill.step': {
        const eventStep = event.step ?? {}
        setState(prev => {
          // SSE step uses step_id; normalize to id for matching
          const eventStepId = eventStep.step_id ?? eventStep.id
          const normalized = normalizeEventStep(eventStep)

          const steps = prev.steps.map(s =>
            s.id === eventStepId ? { ...s, ...normalized } : s
          )
          const currentStep = buildCurrentStep(steps, eventStep)
          return {
            ...prev,
            status: 'active',
            skillName: event.skillName || prev.skillName,
            steps,
            currentStep,
          }
        })
        break
      }
      case 'skill.log': {
        setState(prev => ({
          ...prev,
          logs: [...prev.logs, { message: event.message, time: event.time }],
        }))
        break
      }
      case 'skill.completed': {
        setState(prev => ({
          ...prev,
          status: 'completed',
          result: event.result ?? null,
          steps: prev.steps.map(s => ({ ...s, status: 'completed' })),
          currentStep: null,
        }))
        break
      }
      case 'skill.failed': {
        setState(prev => ({
          ...prev,
          status: 'failed',
          error: event.error || '\u6267\u884c\u5931\u8d25',
          currentStep: null,
        }))
        break
      }
      case 'skill.cancelled': {
        setState(prev => ({
          ...prev,
          status: 'cancelled',
          currentStep: null,
        }))
        break
      }
    }
  }, [skillId])

  // Fetch initial status and build unified step list from steps + step_states
  useEffect(() => {
    if (!skillId) return

    getSkillStatus(skillId)
      .then(data => {
        const s = data.skill ?? data
        const mergedSteps = mergeStepsAndStates(s.steps ?? [], s.step_states ?? [])
        const current = mergedSteps.find(
          step => step.status === 'running' || step.status === 'waiting_input'
        ) || null
        setState({
          status: s.status === 'completed' ? 'completed'
            : s.status === 'failed' ? 'failed'
            : s.status === 'cancelled' ? 'cancelled'
            : 'active',
          skillName: s.display_name || s.skill_name || s.name || skillId,
          steps: mergedSteps,
          currentStep: current,
          logs: s.logs ?? [],
          result: s.result ?? null,
          error: s.error ?? null,
        })
      })
      .catch((err) => {
        // If skill instance not found (e.g. server restart), show error instead of infinite loading
        if (err?.message?.startsWith('404')) {
          setState(prev => ({
            ...prev,
            status: 'failed',
            error: '流程实例不存在（可能服务已重启）',
          }))
        }
      })

    // Poll as fallback (every 2s) in case SSE misses events
    pollIntervalRef.current = setInterval(async () => {
      try {
        const data = await getSkillStatus(skillId)
        const s = data.skill ?? data
        const mergedSteps = mergeStepsAndStates(s.steps ?? [], s.step_states ?? [])
        const current = mergedSteps.find(
          step => step.status === 'running' || step.status === 'waiting_input'
        ) || null
        setState(prev => ({
          ...prev,
          status: s.status === 'completed' ? 'completed'
            : s.status === 'failed' ? 'failed'
            : s.status === 'cancelled' ? 'cancelled'
            : prev.status,
          steps: mergedSteps,
          currentStep: current,
          result: s.result ?? prev.result,
          error: s.error ?? prev.error,
        }))
        if (s.status === 'completed' || s.status === 'failed' || s.status === 'cancelled') {
          clearInterval(pollIntervalRef.current)
        }
      } catch (err) {
        // Stop polling on 404 — skill instance no longer exists (e.g. server restart)
        if (err?.message?.startsWith('404')) {
          clearInterval(pollIntervalRef.current)
          setState(prev => prev.status === 'loading' ? {
            ...prev,
            status: 'failed',
            error: '流程实例不存在（可能服务已重启）',
          } : prev)
        }
      }
    }, 2000)

    return () => {
      clearInterval(pollIntervalRef.current)
    }
  }, [skillId])

  // Listen for SSE events via window event (dispatched from App)
  useEffect(() => {
    function handler(e) {
      handleSkillEvent(e.detail)
    }
    window.addEventListener('skillEvent', handler)
    return () => window.removeEventListener('skillEvent', handler)
  }, [handleSkillEvent])

  // Notify parent on terminal states, passing final state for onCompleted
  useEffect(() => {
    if (notifiedRef.current) return
    if (state.status === 'completed' && onCompleted) {
      notifiedRef.current = true
      onCompleted(state.result ? { result: state.result, steps: state.steps } : undefined)
    }
    if (state.status === 'cancelled' && onCancelled) {
      notifiedRef.current = true
      onCancelled()
    }
  }, [state.status, onCompleted, onCancelled])

  const handleSubmitForm = useCallback(async (stepId, data) => {
    await submitSkillStep(skillId, stepId, data)
  }, [skillId])

  const handleConfirm = useCallback(async () => {
    if (!state.currentStep) return
    setConfirming(true)
    try {
      // ConfirmStepPanel passes data via onConfirm, we use a ref to capture it
      const data = confirmDataRef.current || { confirmed: true }
      await submitSkillStep(skillId, state.currentStep.id, data)
    } catch (err) {
      // Error shown in form panel
    } finally {
      setConfirming(false)
    }
  }, [skillId, state.currentStep])

  const confirmDataRef = useRef({ confirmed: true })

  const handleConfirmWithData = useCallback((data) => {
    confirmDataRef.current = data
    handleConfirm()
  }, [handleConfirm])

  const handleCancelStep = useCallback(async () => {
    try {
      await cancelSkill(skillId)
    } catch {
      // Already cancelled or failed; state will update via SSE/poll
    }
  }, [skillId])

  const handleGoBack = useCallback(async (targetStepId) => {
    if (!skillId) return
    try {
      const data = await goBackSkill(skillId, targetStepId || state.currentStep?.id)
      const s = data.skill ?? data
      const mergedSteps = mergeStepsAndStates(s.steps ?? [], s.step_states ?? [])
      const current = mergedSteps.find(
        step => step.status === 'running' || step.status === 'waiting_input'
      ) || null
      setState(prev => ({
        ...prev,
        steps: mergedSteps,
        currentStep: current,
        skillName: s.display_name || s.skill_name || prev.skillName,
      }))
    } catch {
      // Ignore errors
    }
  }, [skillId, state.currentStep])

  // Loading state
  if (!skillId) {
    return (
      <div className="workbench-panel skill-flow-panel">
        <p className="empty-text">\u6ca1\u6709\u8f6c\u5df2\u542f\u52a8\u7684 Skill</p>
      </div>
    )
  }

  if (state.status === 'loading') {
    return (
      <div className="workbench-panel skill-flow-panel">
        <div className="overview-loading-panel">
          <span className="loading-spinner" />
          <p className="overview-loading-text">\u52a0\u8f7d\u4e2d...</p>
        </div>
      </div>
    )
  }

  const currentStep = state.currentStep
  const stepMode = currentStep ? inferMode(currentStep) : 'auto'
  const currentStepIndex = state.steps.findIndex(s => s.id === currentStep?.id)
  const canGoBack = currentStepIndex > 0

  // Check for custom step renderer first
  const CustomRenderer = currentStep && stepRenderers?.[currentStep.id]

  // Find the step_id of the previous step for "上一步" button
  const prevStepId = canGoBack ? state.steps[currentStepIndex - 1]?.id : null

  return (
    <div className="workbench-panel skill-flow-panel">
      <div className="skill-flow-header">
        <h3 className="skill-flow-title">{state.skillName}</h3>
      </div>

      <StepIndicator steps={state.steps} onStepClick={(stepId) => handleGoBack(stepId)} />

      {state.status === 'completed' && <CompletedPanel result={state.result} />}

      {state.status === 'cancelled' && <CancelledPanel />}

      {state.status === 'failed' && <ErrorPanel error={state.error} />}

      {(state.status === 'active' || state.status === 'loading') && currentStep && (
        <div className="skill-flow-current-step">
          {CustomRenderer ? (
            <CustomRenderer
              stepState={currentStep}
              onSubmit={(data) => handleSubmitForm(currentStep.id, data)}
              onConfirm={handleConfirm}
              onCancel={handleCancelStep}
              confirming={confirming}
            />
          ) : (
            <>
              {stepMode === 'auto' && <AutoStepPanel step={currentStep} />}
              {stepMode === 'form' && (
                <FormStepPanel
                  step={currentStep}
                  onSubmit={handleSubmitForm}
                  onGoBack={() => handleGoBack(prevStepId)}
                  canGoBack={canGoBack}
                />
              )}
              {stepMode === 'confirm' && (
                <ConfirmStepPanel
                  step={currentStep}
                  onConfirm={handleConfirmWithData}
                  onCancel={() => handleGoBack(prevStepId)}
                  confirming={confirming}
                />
              )}
            </>
          )}
        </div>
      )}

      <LogStream logs={state.logs} />

      <div className="skill-flow-footer">
        {state.status === 'active' && (
          <button
            type="button"
            className="workbench-primary-button workbench-primary-button--secondary skill-flow-cancel-btn"
            onClick={handleCancelStep}
          >
            取消流程
          </button>
        )}
      </div>
    </div>
  )
}

// --- Normalize SSE step event (step_id → id) ---

function normalizeEventStep(eventStep) {
  const id = eventStep.step_id ?? eventStep.id
  return {
    id,
    step_id: eventStep.step_id,  // keep original for reference
    name: eventStep.name ?? id,
    status: normalizeStepStatus(eventStep.status),
    output_data: eventStep.output_data ?? null,
    progress: eventStep.progress ?? 0,
  }
}
