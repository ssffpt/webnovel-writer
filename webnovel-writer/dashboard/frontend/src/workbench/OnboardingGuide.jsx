import { useCallback, useEffect, useLayoutEffect, useState } from 'react'

const STORAGE_KEY = 'workbench-guide-done'

const STEPS = [
  {
    target: null,
    title: '欢迎来到网文创作工作台',
    description:
      '这里是你创作网文的主阵地。接下来带你快速了解工作台的核心功能，只需 3 步。',
  },
  {
    target: 'topbar',
    title: '页面导航',
    description:
      '顶栏的四个标签页是你的主要工作区域：章节页写正文、大纲页规划故事结构、设定页管理人物与世界观、总览页查看项目全貌。推荐先从大纲页开始规划。',
  },
  {
    target: 'main',
    title: '工作区',
    description:
      '中间区域是当前页面的主工作区。你可以浏览文件列表、编辑内容、保存修改。每个页面的左侧是文件导航，中间是编辑器。',
  },
  {
    target: 'sidebar',
    title: 'AI 助手',
    description:
      '右侧是 AI 创作助手。用自然语言告诉它你想做什么，它会推荐合适的动作；动作卡让你一键触发写作、规划、审查等任务；任务面板实时展示执行进度。',
  },
]

export function hasGuideCompleted() {
  return localStorage.getItem(STORAGE_KEY) === '1'
}

export function markGuideDone() {
  localStorage.setItem(STORAGE_KEY, '1')
}

export function resetGuideDone() {
  localStorage.removeItem(STORAGE_KEY)
}

export default function OnboardingGuide({ step, onNext, onPrev, onClose, targets }) {
  const [bubblePos, setBubblePos] = useState({ top: 0, left: 0, placement: 'center' })

  const currentStep = STEPS[step - 1]
  if (!currentStep) return null

  const isFirst = step === 1
  const isLast = step === STEPS.length

  // Recalculate target position
  useLayoutEffect(() => {
    if (!currentStep.target || !targets) {
      setBubblePos({ top: window.innerHeight / 2, left: window.innerWidth / 2, placement: 'center' })
      return
    }

    const el = targets[currentStep.target]?.current
    if (!el) return

    const rect = el.getBoundingClientRect()
    const bubbleWidth = 380
    const bubbleHeight = 200
    const gap = 12

    let top, left, placement
    if (rect.bottom + gap + bubbleHeight < window.innerHeight) {
      top = rect.bottom + gap
      left = rect.left + rect.width / 2 - bubbleWidth / 2
      placement = 'below'
    } else {
      top = rect.top - gap - bubbleHeight
      left = rect.left + rect.width / 2 - bubbleWidth / 2
      placement = 'above'
    }

    left = Math.max(12, Math.min(left, window.innerWidth - bubbleWidth - 12))
    top = Math.max(12, top)

    setBubblePos({ top, left, placement })
  }, [step, currentStep.target, targets])

  // Prevent body scroll when guide is active
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  const handleNext = useCallback(() => {
    if (isLast) {
      markGuideDone()
      onClose()
    } else {
      onNext()
    }
  }, [isLast, onClose, onNext])

  const handleSkip = useCallback(() => {
    markGuideDone()
    onClose()
  }, [onClose])

  // Highlight class for target element
  useEffect(() => {
    if (!currentStep.target || !targets) return
    const el = targets[currentStep.target]?.current
    if (!el) return

    el.classList.add('onboarding-highlight')
    return () => el.classList.remove('onboarding-highlight')
  }, [step, currentStep.target, targets])

  return (
    <>
      {/* Semi-transparent backdrop — z-index below highlighted elements but above page */}
      <div className="onboarding-overlay" />

      {/* Step indicator — z-index above everything */}
      <div className="onboarding-step-indicator">
        {step} / {STEPS.length}
      </div>

      {/* Bubble — z-index above highlighted elements so buttons are always clickable */}
      <div
        className={`onboarding-bubble onboarding-bubble--${bubblePos.placement}`}
        style={{
          top: bubblePos.top,
          left: bubblePos.left,
          position: currentStep.target ? 'absolute' : 'fixed',
        }}
      >
        <h3 className="onboarding-bubble-title">{currentStep.title}</h3>
        <p className="onboarding-bubble-desc">{currentStep.description}</p>

        <div className="onboarding-bubble-actions">
          {!isFirst && (
            <button type="button" className="workbench-nav-button" onClick={onPrev}>
              上一步
            </button>
          )}
          <button type="button" className="workbench-primary-button" onClick={handleNext}>
            {isLast ? '开始使用' : '下一步'}
          </button>
          <button type="button" className="onboarding-skip-button" onClick={handleSkip}>
            跳过引导
          </button>
        </div>

        {/* Arrow */}
        {currentStep.target && (
          <div className={`onboarding-bubble-arrow onboarding-bubble-arrow--${bubblePos.placement}`} />
        )}
      </div>
    </>
  )
}
