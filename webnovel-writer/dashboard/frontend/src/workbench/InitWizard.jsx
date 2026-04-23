import { useState } from 'react'
import { startSkill } from '../api.js'
import SkillFlowPanel from './SkillFlowPanel.jsx'

// Step 1: StoryCoreForm — rendered by SkillFlowPanel's default FormStepPanel
// Step 2: CharacterForm — rendered by SkillFlowPanel's default FormStepPanel
// Step 3: GoldenFingerForm — rendered by SkillFlowPanel's default FormStepPanel
// Step 4: WorldBuildingForm — rendered by SkillFlowPanel's default FormStepPanel
const INIT_STEP_RENDERERS = {
  step_1: null,
  step_2: null,
  step_3: null,
  step_4: null,
  step_5: CreativityPackageSelector,
  step_6: SummaryConfirmation,
}

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

// 开始画面
function StartScreen({ onStart }) {
  return (
    <div className="init-wizard-start">
      <h2>创建新小说</h2>
      <p>通过 6 步向导初始化项目，采集故事核、角色、金手指、世界观等核心设定。</p>
      <button type="button" className="workbench-primary-button" onClick={onStart}>
        ＋ 开始创建
      </button>
    </div>
  )
}

/**
 * 6 步初始化向导。
 * 基于 SkillFlowPanel，但通过 stepRenderers 自定义 Step 5/6 的 UI。
 *
 * @param {function} onCompleted - 创建成功回调
 * @param {function} onCancelled - 取消回调
 */
export default function InitWizard({ onCompleted, onCancelled }) {
  const [skillId, setSkillId] = useState(null)
  const [startError, setStartError] = useState('')

  const handleStart = async () => {
    setStartError('')
    try {
      const timestamp = Date.now()
      const result = await startSkill('init', {
        context: { project_root: `./projects/novel-${timestamp}` }
      })
      setSkillId(result.id)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : '启动失败')
    }
  }

  if (!skillId) {
    return (
      <div className="workbench-panel init-wizard">
        <StartScreen onStart={handleStart} />
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
