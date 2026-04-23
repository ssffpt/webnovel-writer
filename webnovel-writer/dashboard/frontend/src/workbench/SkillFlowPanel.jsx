import { useCallback, useEffect, useRef, useState } from 'react'
import { getSkillStatus, submitSkillStep, cancelSkill } from '../api.js'

// --- Step Progress Bar ---

function StepIndicator({ steps }) {
  return (
    <div className="skill-flow-step-bar">
      {steps.map((step, i) => (
        <div
          key={step.id}
          className={`skill-flow-step-item ${step.status === 'completed' ? 'completed' : ''} ${step.status === 'running' ? 'running' : ''}`}
        >
          <span className="skill-flow-step-marker">
            {step.status === 'completed' ? '\u2713' : step.status === 'running' ? '\u25CF' : '\u25CB'}
          </span>
          <span className="skill-flow-step-label">{step.name}</span>
          {i < steps.length - 1 && <span className="skill-flow-step-connector" />}
        </div>
      ))}
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

function FormStepPanel({ step, onSubmit }) {
  const [formData, setFormData] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const schema = step.schema ?? step.output_data?.schema ?? {}

  function handleChange(field, value) {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setFormError('')
    setSubmitting(true)
    try {
      await onSubmit(step.id, formData)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '\u63d0\u4ea4\u5931\u8d25')
    } finally {
      setSubmitting(false)
    }
  }

  const fields = schema.fields ?? []

  return (
    <div className="skill-flow-step-panel skill-flow-step-panel--form">
      <h4 className="skill-flow-step-title">{step.name || step.id}</h4>
      <form onSubmit={handleSubmit} className="skill-flow-form">
        {fields.length === 0 && (
          <p className="skill-flow-no-fields">\u8be5\u6b65\u9aa4\u6ca1\u6709\u8868\u5355\u5b57\u6bb5</p>
        )}
        {fields.map(field => (
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
                placeholder={field.placeholder}
                required={field.required}
                rows={4}
              />
            ) : (
              <input
                type={field.type || 'text'}
                className="skill-flow-form-input"
                value={formData[field.name] ?? ''}
                onChange={e => handleChange(field.name, e.target.value)}
                placeholder={field.placeholder}
                required={field.required}
              />
            )}
            {field.description && (
              <span className="skill-flow-form-hint">{field.description}</span>
            )}
          </div>
        ))}
        {formError && <p className="error-text">{formError}</p>}
        <div className="skill-flow-form-actions">
          <button
            type="submit"
            className="workbench-primary-button"
            disabled={submitting}
          >
            {submitting ? '\u63d0\u4ea4\u4e2d...' : '\u63d0\u4ea4'}
          </button>
        </div>
      </form>
    </div>
  )
}

// --- Confirm Step Panel ---

function ConfirmStepPanel({ step, onConfirm, onCancel, confirming }) {
  return (
    <div className="skill-flow-step-panel skill-flow-step-panel--confirm">
      <h4 className="skill-flow-step-title">{step.name || step.id}</h4>
      {step.output_data?.message && (
        <p className="skill-flow-confirm-message">{step.output_data.message}</p>
      )}
      {step.output_data?.result != null && (
        <pre className="skill-flow-confirm-result">
          {typeof step.output_data.result === 'object'
            ? JSON.stringify(step.output_data.result, null, 2)
            : String(step.output_data.result)}
        </pre>
      )}
      <div className="skill-flow-confirm-actions">
        <button
          type="button"
          className="workbench-nav-button"
          onClick={onCancel}
          disabled={confirming}
        >
          \u53d6\u6d88
        </button>
        <button
          type="button"
          className="workbench-primary-button"
          onClick={onConfirm}
          disabled={confirming}
        >
          {confirming ? '\u5904\u7406\u4e2d...' : '\u786e\u8ba4'}
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
          skillName: s.skill_name || s.name || skillId,
          steps: mergedSteps,
          currentStep: current,
          logs: s.logs ?? [],
          result: s.result ?? null,
          error: s.error ?? null,
        })
      })
      .catch(() => {
        // If status fetch fails, just wait for SSE events
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
      } catch {
        // Ignore polling errors
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
      await submitSkillStep(skillId, state.currentStep.id, { confirmed: true })
    } catch (err) {
      // Error shown in form panel
    } finally {
      setConfirming(false)
    }
  }, [skillId, state.currentStep])

  const handleCancelStep = useCallback(async () => {
    try {
      await cancelSkill(skillId)
    } catch {
      // Already cancelled or failed; state will update via SSE/poll
    }
  }, [skillId])

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

  // Check for custom step renderer first
  const CustomRenderer = currentStep && stepRenderers?.[currentStep.id]

  return (
    <div className="workbench-panel skill-flow-panel">
      <div className="skill-flow-header">
        <h3 className="skill-flow-title">\u6b63\u5728\u6267\u884c\uff1a{state.skillName}</h3>
      </div>

      <StepIndicator steps={state.steps} />

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
                <FormStepPanel step={currentStep} onSubmit={handleSubmitForm} />
              )}
              {stepMode === 'confirm' && (
                <ConfirmStepPanel
                  step={currentStep}
                  onConfirm={handleConfirm}
                  onCancel={handleCancelStep}
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
            className="workbench-nav-button"
            onClick={handleCancelStep}
          >
            \u53d6\u6d88
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
