import { useState } from 'react'
import SkillFlowPanel from './SkillFlowPanel.jsx'
import RAGConfig from './RAGConfig.jsx'
import { startSkill } from '../api.js'

// --- Skill Test Wrapper ---

function SkillTestWrapper() {
  const [skillId, setSkillId] = useState(null)
  const [startError, setStartError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [starting, setStarting] = useState(false)

  async function handleStartTest() {
    setStartError('')
    setStarting(true)
    try {
      const result = await startSkill('echo', {})
      setSkillId(result.skill_id || result.id || result.skillId)
    } catch (err) {
      setStartError(err instanceof Error ? err.message : '启动 Skill 失败')
    } finally {
      setStarting(false)
    }
  }

  function handleCompleted() {
    setSuccessMsg('Skill 执行完成！')
    setTimeout(() => {
      setSuccessMsg('')
      setSkillId(null)
    }, 3000)
  }

  function handleCancelled() {
    setSkillId(null)
  }

  return (
    <div className="skill-test-wrapper">
      {!skillId ? (
        <div>
          <h3>Skill 流程测试</h3>
          <p className="skill-test-desc">点击下方按钮启动 echo Skill，测试 SkillFlowPanel 组件。</p>
          <button
            type="button"
            className="workbench-primary-button"
            onClick={handleStartTest}
            disabled={starting}
          >
            {starting ? '启动中...' : '测试 Skill 流程'}
          </button>
          {startError && <p className="error-text" style={{ marginTop: 8 }}>{startError}</p>}
        </div>
      ) : (
        <>
          {successMsg && (
            <div className="skill-test-success">{successMsg}</div>
          )}
          <SkillFlowPanel
            skillId={skillId}
            onCompleted={handleCompleted}
            onCancelled={handleCancelled}
          />
        </>
      )}
    </div>
  )
}

// --- Main Component ---

export default function ConfigPage() {
  return (
    <section className="workbench-page">
      <div className="page-header">
        <h2>配置</h2>
      </div>

      <div className="config-page-grid">
        <div className="workbench-panel config-panel-left">
          <SkillTestWrapper />
        </div>

        <div className="workbench-panel config-panel-right">
          <RAGConfig />
        </div>
      </div>
    </section>
  )
}
