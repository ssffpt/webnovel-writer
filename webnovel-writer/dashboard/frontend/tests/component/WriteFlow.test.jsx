import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
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
import WriteFlow from '@/workbench/WriteFlow.jsx'
import * as WriteFlowModule from '@/workbench/WriteFlow.jsx'

describe('WriteFlow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    startSkill.mockResolvedValue({ id: 'write-skill-456' })
  })

  // --- Happy Path ---
  it('renders WriteStartScreen with start button when skillId is null', () => {
    const { container } = render(
      <WriteFlow projectRoot="/test/project" chapterNum={1} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const btn = container.querySelector('button')
    expect(btn).not.toBeNull()
    expect(btn.textContent).toContain('开始创作')
  })

  it('renders AI 创作 heading with chapter number', () => {
    const { container } = render(
      <WriteFlow projectRoot="/test/project" chapterNum={3} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    expect(container.textContent).toContain('AI 创作 — 第3章')
  })

  it('calls startSkill("write") with correct params when start button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <WriteFlow projectRoot="/test/project" chapterNum={1} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const btn = screen.getByRole('button', { name: /开始创作/i })
    await user.click(btn)
    await waitFor(() => {
      expect(startSkill).toHaveBeenCalledWith('write', {
        mode: 'standard',
        context: {
          project_root: '/test/project',
          chapter_num: 1,
        },
      })
    })
  })

  it('renders SkillFlowPanel after start button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <WriteFlow projectRoot="/test/project" chapterNum={1} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const btn = screen.getByRole('button', { name: /开始创作/i })
    await user.click(btn)

    await waitFor(() => {
      expect(screen.getByTestId('skill-flow-panel')).toBeInTheDocument()
      expect(screen.getByTestId('skill-flow-panel').dataset.skillId).toBe('write-skill-456')
    })
  })

  // --- Edge Case 1: mode="fast" passes fast mode to startSkill ---
  it('passes mode=fast to startSkill when fast mode is selected', async () => {
    const user = userEvent.setup()
    render(
      <WriteFlow projectRoot="/test/project" chapterNum={1} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const select = screen.getByRole('combobox')
    await user.selectOptions(select, 'fast')

    const btn = screen.getByRole('button', { name: /开始创作/i })
    await user.click(btn)

    await waitFor(() => {
      expect(startSkill).toHaveBeenCalledWith('write', {
        mode: 'fast',
        context: {
          project_root: '/test/project',
          chapter_num: 1,
        },
      })
    })
  })

  it('shows fast mode hint text when fast mode is selected', async () => {
    const user = userEvent.setup()
    render(
      <WriteFlow projectRoot="/test/project" chapterNum={1} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )
    const select = screen.getByRole('combobox')
    await user.selectOptions(select, 'fast')

    expect(screen.getByText(/快速流程：起草 → 六维审查 → 润色（跳过风格适配）/)).toBeInTheDocument()
  })

  // --- Edge Case 2: Step 3 ReviewResultsDisplay renders six-dimension scores ---
  describe('ReviewResultsDisplay', () => {
    const ReviewResultsDisplay = WriteFlowModule.ReviewResultsDisplay

    it('renders six-dimension review results with score bars', () => {
      const stepState = {
        output_data: {
          total_score: 8.5,
          issues_count: 2,
          critical_count: 0,
          review_results: [
            { dimension: '剧情', score: 9, passed: true, issues: [] },
            { dimension: '人物', score: 8, passed: true, issues: [] },
            { dimension: '文笔', score: 8, passed: true, issues: [] },
          ],
        },
      }

      render(<ReviewResultsDisplay stepState={stepState} />)

      expect(screen.getByText('六维审查')).toBeInTheDocument()
      expect(screen.getByText('总分：8.5/10')).toBeInTheDocument()
      expect(screen.getByText('2 个问题')).toBeInTheDocument()
      expect(screen.getByText('剧情')).toBeInTheDocument()
      expect(screen.getByText('人物')).toBeInTheDocument()
      expect(screen.getByText('文笔')).toBeInTheDocument()
    })

    it('shows critical badge when there are critical issues', () => {
      const stepState = {
        output_data: {
          total_score: 6,
          issues_count: 3,
          critical_count: 2,
          review_results: [
            { dimension: '剧情', score: 6, passed: false, issues: [{ severity: 'critical', message: '严重问题' }] },
          ],
        },
      }

      render(<ReviewResultsDisplay stepState={stepState} />)

      expect(screen.getByText('2 个严重问题')).toBeInTheDocument()
    })

    it('renders issue details in expandable section', () => {
      const stepState = {
        output_data: {
          total_score: 7,
          issues_count: 1,
          critical_count: 1,
          review_results: [
            {
              dimension: '剧情',
              score: 7,
              passed: false,
              issues: [
                { severity: 'high', message: '情节推进过快', suggestion: '增加过渡段落' },
              ],
            },
          ],
        },
      }

      render(<ReviewResultsDisplay stepState={stepState} />)

      expect(screen.getByText('情节推进过快')).toBeInTheDocument()
      expect(screen.getByText('增加过渡段落')).toBeInTheDocument()
    })
  })

  // --- DraftConfirm component ---
  describe('DraftConfirm', () => {
    const DraftConfirm = WriteFlowModule.DraftConfirm

    it('renders draft text and word count', () => {
      const stepState = {
        output_data: {
          draft_text: '这是草稿正文',
          word_count: 100,
        },
      }

      render(<DraftConfirm stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText('正文草稿')).toBeInTheDocument()
      expect(screen.getByText('字数：100')).toBeInTheDocument()
      expect(screen.getByText('这是草稿正文')).toBeInTheDocument()
    })

    it('shows edit textarea when 编辑修改 is clicked', async () => {
      const user = userEvent.setup()
      const stepState = {
        output_data: {
          draft_text: '草稿内容',
          word_count: 50,
        },
      }

      render(<DraftConfirm stepState={stepState} onSubmit={vi.fn()} />)

      const editBtn = screen.getByRole('button', { name: /编辑修改/i })
      await user.click(editBtn)

      expect(screen.getByRole('textbox')).toBeInTheDocument()
    })

    it('calls onSubmit with confirmed:true when 确认草稿 is clicked', async () => {
      const user = userEvent.setup()
      const onSubmit = vi.fn()
      const stepState = {
        output_data: {
          draft_text: '草稿内容',
          word_count: 50,
        },
      }

      render(<DraftConfirm stepState={stepState} onSubmit={onSubmit} />)

      const confirmBtn = screen.getByRole('button', { name: /确认草稿/i })
      await user.click(confirmBtn)

      expect(onSubmit).toHaveBeenCalledWith({ confirmed: true })
    })
  })

  // --- StyleAdaptConfirm component ---
  describe('StyleAdaptConfirm', () => {
    const StyleAdaptConfirm = WriteFlowModule.StyleAdaptConfirm

    it('renders style adaptation results', () => {
      const stepState = {
        output_data: {
          adapted_text: '适配后正文',
          has_changes: true,
          changes_summary: '已适配作者风格',
        },
      }

      render(<StyleAdaptConfirm stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText('风格适配')).toBeInTheDocument()
      expect(screen.getByText('已适配作者风格')).toBeInTheDocument()
      expect(screen.getByText('高亮部分为风格调整')).toBeInTheDocument()
    })

    it('shows 无需风格调整 when no changes needed', () => {
      const stepState = {
        output_data: {
          has_changes: false,
        },
      }

      render(<StyleAdaptConfirm stepState={stepState} onSubmit={vi.fn()} />)

      expect(screen.getByText('无需风格调整')).toBeInTheDocument()
    })
  })

  // --- DataAgentDisplay component ---
  describe('DataAgentDisplay', () => {
    const DataAgentDisplay = WriteFlowModule.DataAgentDisplay

    it('renders data agent results', () => {
      const stepState = {
        output_data: {
          results: {
            chapter_saved: true,
            entities_extracted: 42,
            summary_generated: true,
            scenes_sliced: 5,
            debts_detected: 3,
          },
        },
      }

      render(<DataAgentDisplay stepState={stepState} />)

      expect(screen.getByText('Data Agent')).toBeInTheDocument()
      expect(screen.getByText('正文已保存：是')).toBeInTheDocument()
      expect(screen.getByText('实体提取：42 个')).toBeInTheDocument()
      expect(screen.getByText('摘要生成：完成')).toBeInTheDocument()
      expect(screen.getByText('场景切片：5 个')).toBeInTheDocument()
      expect(screen.getByText('债务检测：3 条')).toBeInTheDocument()
    })
  })

  // --- GitBackupDisplay component ---
  describe('GitBackupDisplay', () => {
    const GitBackupDisplay = WriteFlowModule.GitBackupDisplay

    it('shows success message with commit hash', () => {
      const stepState = {
        output_data: {
          success: true,
          commit_hash: 'abc1234',
        },
      }

      render(<GitBackupDisplay stepState={stepState} />)

      expect(screen.getByText(/Git 提交成功：abc1234/)).toBeInTheDocument()
    })

    it('shows skipped message when git is skipped', () => {
      const stepState = {
        output_data: {
          skipped: true,
          reason: '非 Git 仓库',
        },
      }

      render(<GitBackupDisplay stepState={stepState} />)

      expect(screen.getByText(/Git 备份已跳过（非 Git 仓库）/)).toBeInTheDocument()
    })
  })

  // --- Error Case: Shows error message when startSkill fails ---
  it('shows error message when startSkill fails', async () => {
    startSkill.mockRejectedValue(new Error('启动创作失败'))
    const user = userEvent.setup()

    render(
      <WriteFlow projectRoot="/test/project" chapterNum={1} onCompleted={vi.fn()} onCancelled={vi.fn()} />
    )

    const btn = screen.getByRole('button', { name: /开始创作/i })
    await user.click(btn)

    await waitFor(() => {
      expect(screen.getByText(/启动创作失败/)).toBeInTheDocument()
    })
  })
})
