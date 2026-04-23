import { useEffect, useState } from 'react'
import { startSkill, fetchPendingSkills, cancelSkill } from '../api.js'
import SkillFlowPanel from './SkillFlowPanel.jsx'

// Step 5: 创意约束包选择器
function CreativityPackageSelector({ stepState, onSubmit }) {
  const packages = stepState.output_data?.packages || []
  const [selectedId, setSelectedId] = useState(null)

  return (
    <div>
      <h3>选择创意约束包</h3>
      <div className="package-cards">
        {packages.map(pkg => (
          <div
            key={pkg.id}
            className={`package-card ${selectedId === pkg.id ? 'selected' : ''}`}
            onClick={() => setSelectedId(pkg.id)}
            role="button"
            tabIndex={0}
            onKeyDown={e => e.key === 'Enter' && setSelectedId(pkg.id)}
          >
            <h4>{pkg.name}</h4>
            <p>{pkg.description}</p>
          </div>
        ))}
      </div>
      <button onClick={() => onSubmit({ selected_package_id: selectedId })} disabled={!selectedId}>
        确认选择
      </button>
    </div>
  )
}

// Step 6: 摘要确认
function SummaryConfirmation({ stepState, onSubmit }) {
  const { summary, gate_passed, missing_items } = stepState.output_data || {}

  if (!gate_passed) {
    return (
      <div className="gate-warning">
        <h3>以下必填项尚未完成</h3>
        <ul>
          {(missing_items || []).map(item => <li key={item}>{item}</li>)}
        </ul>
        <p>请返回对应步骤补填</p>
      </div>
    )
  }

  return (
    <div>
      <h3>项目摘要</h3>
      <pre>{summary}</pre>
      <button onClick={() => onSubmit({ confirmed: true })}>确认创建</button>
    </div>
  )
}

// Step renderers — defined after the components to avoid const hoisting issues
const INIT_STEP_RENDERERS = {
  step_1: null,
  step_2: null,
  step_3: null,
  step_4: null,
  step_5: CreativityPackageSelector,
  step_6: SummaryConfirmation,
}

// 开始画面
function StartScreen({ onStart, onResume, hasPending }) {
  return (
    <div className="init-wizard-start">
      <h2>创建新小说</h2>
      <p>通过 6 步向导初始化项目，采集故事核、角色、金手指、世界观等核心设定。</p>
      <div className="init-wizard-actions">
        {hasPending && (
          <button type="button" className="workbench-primary-button" onClick={onResume}>
            继续上次配置
          </button>
        )}
        <button type="button" className={hasPending ? 'workbench-primary-button workbench-primary-button--secondary' : 'workbench-primary-button'} onClick={onStart}>
          ＋ 开始创建
        </button>
      </div>
    </div>
  )
}

/**
 * 6 步初始化向导。
 * 基于 SkillFlowPanel，但通过 stepRenderers 自定义 Step 5/6 的 UI。
 * 支持断点续传：启动时检查是否有未完成的 init 流程，如有则直接恢复。
 *
 * @param {function} onCompleted - 创建成功回调
 * @param {function} onCancelled - 取消回调
 */
export default function InitWizard({ onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)
  const [startError, setStartError] = useState('')
  const [pendingInstance, setPendingInstance] = useState(null)
  const [checking, setChecking] = useState(true)

  // Check for pending init skill on mount
  useEffect(() => {
    let cancelled = false
    async function check() {
      try {
        const data = await fetchPendingSkills('init')
        if (cancelled) return
        const instances = data.instances || []
        if (instances.length > 0) {
          // Use the most recent one
          setPendingInstance(instances[instances.length - 1])
        }
      } catch {
        // API may fail if no project root, ignore
      } finally {
        setChecking(false)
      }
    }
    check()
    return () => { cancelled = true }
  }, [])

  const handleStart = async () => {
    setStartError('')
    try {
      // If there's a pending instance, cancel it first
      if (pendingInstance) {
        try { await cancelSkill(pendingInstance.id) } catch {}
        setPendingInstance(null)
      }
      const timestamp = Date.now()
      const result = await startSkill('init', {
        context: { project_root: `./projects/novel-${timestamp}` }
      })
      setSkillId(result.id)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : '启动失败')
    }
  }

  const handleResume = () => {
    if (pendingInstance) {
      setSkillId(pendingInstance.id)
      setPendingInstance(null)
    }
  }

  if (checking) {
    return (
      <div className="workbench-panel init-wizard">
        <div className="overview-loading-panel">
          <span className="loading-spinner" />
          <p className="overview-loading-text">检查中...</p>
        </div>
      </div>
    )
  }

  if (!skillId) {
    return (
      <div className="workbench-panel init-wizard">
        <StartScreen
          onStart={handleStart}
          onResume={handleResume}
          hasPending={!!pendingInstance}
        />
        {pendingInstance && (
          <p className="init-wizard-resume-hint">
            检测到未完成的配置（第 {pendingInstance.completed_steps + 1}/{pendingInstance.total_steps} 步）
          </p>
        )}
        {startError && <p className="error-text">{startError}</p>}
      </div>
    )
  }

  return (
    <SkillFlowPanel
      skillId={skillId}
      stepRenderers={INIT_STEP_RENDERERS}
      onCompleted={onCompleted}
      onCancelled={onCancelled}
    />
  )
}

export { CreativityPackageSelector, SummaryConfirmation }
