import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock the api module
vi.mock('@/api.js', () => ({
  startSkill: vi.fn(),
  submitSkillStep: vi.fn(),
  getSkillStatus: vi.fn(),
  cancelSkill: vi.fn(),
}))

// Mock SkillFlowPanel
vi.mock('@/workbench/SkillFlowPanel.jsx', () => ({
  default: function MockSkillFlowPanel({ skillId, stepRenderers, onCompleted, onCancelled }) {
    return <div data-testid="skill-flow-panel" data-skill-id={skillId} />
  },
}))

import { startSkill } from '@/api.js'
import PlanFlow from '@/workbench/PlanFlow.jsx'
import * as PlanFlowModule from '@/workbench/PlanFlow.jsx'

describe('PlanFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    startSkill.mockResolvedValue({ id: 'plan-skill-456' })
  })

  // --- Happy Path ---
  it('renders PlanStartScreen with start button when skillId is null', () => {
    const { container } = render(
      <PlanFlow projectRoot="/test/project" onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const btn = container.querySelector('button')
    expect(btn).not.toBeNull()
    expect(btn.textContent).toContain('开始规划')
  })

  it('calls startSkill("plan") and sets skillId when start button is clicked', async () => {
    const user = userEvent.setup()
    const onCancelled = vi.fn()
    render(
      <PlanFlow projectRoot="/test/project" onCompleted={vi.fn()} onCancelled={onCancelled} />
    )
    const btn = screen.getByRole('button', { name: /开始规划/i })
    await user.click(btn)
    await waitFor(() => {
      expect(startSkill).toHaveBeenCalledWith('plan', {
        context: {
          project_root: '/test/project',
        },
      })
    })
  })

  it('renders SkillFlowPanel after start button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <PlanFlow projectRoot="/test/project" onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const btn = screen.getByRole('button', { name: /开始规划/i })
    await user.click(btn)

    await waitFor(() => {
      expect(screen.getByTestId('skill-flow-panel')).toBeInTheDocument()
      expect(screen.getByTestId('skill-flow-panel').dataset.skillId).toBe('plan-skill-456')
    })
  })

  // --- Edge Case 1: BeatTableViewer correctly renders beat table ---
  describe('BeatTableViewer', () => {
    const BeatTableViewer = PlanFlowModule.BeatTableViewer

    it('renders beat table with beats data', () => {
      // act 字段对应后端 _fallback_beat_sheet 返回的 "开端/发展/高潮"
      const beats = [
        { chapter: 1, act: '开端', event: '主角初登场', emotion_curve: '平静' },
        { chapter: 2, act: '发展', event: '危机出现', emotion_curve: '紧张' },
      ]
      const stepState = { output_data: { beats } }

      render(<BeatTableViewer stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText('卷节拍表')).toBeInTheDocument()
      expect(screen.getByText('第1章')).toBeInTheDocument()
      expect(screen.getByText('开端')).toBeInTheDocument()
      expect(screen.getByText('主角初登场')).toBeInTheDocument()
      expect(screen.getByText('第2章')).toBeInTheDocument()
      expect(screen.getByText('发展')).toBeInTheDocument()
    })

    it('shows climax badge for climax beats', () => {
      // act='高潮' 且 is_climax=true 时，act列和badge都会显示"高潮"
      const beats = [
        { chapter: 5, act: '高潮', event: '决战', is_climax: true },
      ]
      const stepState = { output_data: { beats } }

      render(<BeatTableViewer stepState={stepState} onSubmit={vi.fn()} />)

      // "高潮" 出现在两处：act列和climax-badge
      const climaxBadges = screen.getAllByText('高潮')
      expect(climaxBadges).toHaveLength(2)
      // 第二个是 climax badge
      expect(climaxBadges[1]).toHaveClass('climax-badge')
    })

    it('calls onSubmit with confirmed:true when confirm button clicked', async () => {
      const onSubmit = vi.fn()
      const user = userEvent.setup()
      const stepState = { output_data: { beats: [] } }

      render(<BeatTableViewer stepState={stepState} onSubmit={onSubmit} />)

      const confirmBtn = screen.getByRole('button', { name: /确认节拍表/i })
      await user.click(confirmBtn)

      expect(onSubmit).toHaveBeenCalledWith({ confirmed: true })
    })
  })

  // --- Edge Case 2: ChapterOutlinesViewer correctly renders chapter outlines ---
  describe('ChapterOutlinesViewer', () => {
    const ChapterOutlinesViewer = PlanFlowModule.ChapterOutlinesViewer

    it('renders chapter outlines list', () => {
      const outlines = [
        { chapter: 1, title: '初入江湖', summary: '主角下山历练' },
        { chapter: 2, title: '江湖风波', summary: '遭遇第一个敌人' },
      ]
      const stepState = { output_data: { chapter_outlines: outlines } }

      render(<ChapterOutlinesViewer stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText('章节大纲')).toBeInTheDocument()
      expect(screen.getByText('初入江湖')).toBeInTheDocument()
      expect(screen.getByText('主角下山历练')).toBeInTheDocument()
      expect(screen.getByText('江湖风波')).toBeInTheDocument()
    })

    it('shows progress percentage when generating', () => {
      const stepState = {
        progress: 0.5,
        output_data: {
          chapter_outlines: [],
          total_generated: 6,
        },
      }

      render(<ChapterOutlinesViewer stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText(/50%/)).toBeInTheDocument()
      expect(screen.getByText(/正在生成\.\.\./)).toBeInTheDocument()
    })

    it('shows completed message when progress is 100%', () => {
      const stepState = {
        progress: 1,
        output_data: {
          chapter_outlines: [],
          total_generated: 6,
        },
      }

      render(<ChapterOutlinesViewer stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText(/已生成 6 章大纲/)).toBeInTheDocument()
    })

    // Note: ChapterOutlinesViewer does not have a "done" button.
    // The confirm flow is handled by BeatTableViewer's "确认节拍表" button.
  })

  // --- Error Case: Shows error message when startSkill fails ---
  it('shows error message when startSkill fails', async () => {
    startSkill.mockRejectedValue(new Error('启动规划失败'))
    const user = userEvent.setup()
    const onCancelled = vi.fn()

    render(
      <PlanFlow projectRoot="/test/project" onCompleted={vi.fn()} onCancelled={onCancelled} />
    )

    const btn = screen.getByRole('button', { name: /开始规划/i })
    await user.click(btn)

    await waitFor(() => {
      expect(screen.getByText(/启动规划失败/)).toBeInTheDocument()
    })
  })

  it('allows retry after error', async () => {
    startSkill
      .mockRejectedValueOnce(new Error('启动规划失败'))
      .mockResolvedValueOnce({ id: 'plan-skill-789' })

    const user = userEvent.setup()
    render(
      <PlanFlow projectRoot="/test/project" onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )

    // First click - will fail
    const btn1 = screen.getByRole('button', { name: /开始规划/i })
    await user.click(btn1)

    await waitFor(() => {
      expect(screen.getByText(/启动规划失败/)).toBeInTheDocument()
    })

    // Click retry button
    const retryBtn = screen.getByRole('button', { name: /重试/i })
    await user.click(retryBtn)

    await waitFor(() => {
      expect(startSkill).toHaveBeenCalledTimes(2)
    })
  })
})