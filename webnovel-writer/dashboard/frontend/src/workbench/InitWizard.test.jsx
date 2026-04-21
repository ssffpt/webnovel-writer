import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock the api module
vi.mock('../api.js', () => ({
  startSkill: vi.fn(),
  submitSkillStep: vi.fn(),
  getSkillStatus: vi.fn(),
  cancelSkill: vi.fn(),
}))

// Mock SkillFlowPanel
vi.mock('./SkillFlowPanel.jsx', () => ({
  default: function MockSkillFlowPanel({ skillId, stepRenderers, onCompleted, onCancelled }) {
    return null
  },
}))

import { startSkill, submitSkillStep } from '../api.js'
import InitWizard from './InitWizard.jsx'
import * as InitWizardModule from './InitWizard.jsx'

describe('InitWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    startSkill.mockResolvedValue({ id: 'skill-123' })
    submitSkillStep.mockResolvedValue({})
  })

  // --- Happy Path ---
  it('renders StartScreen with a start button when skillId is null', async () => {
    const { container } = render(<InitWizard onCompleted={vi.fn()} onCancelled={vi.fn()} />)
    const btn = container.querySelector('button')
    expect(btn).not.toBeNull()
    expect(btn.textContent).toContain('\u5f00\u59cb\u521b\u5efa')
  })

  it('calls startSkill("init") and sets skillId when start button is clicked', async () => {
    const user = userEvent.setup()
    render(<InitWizard onCompleted={vi.fn()} onCancelled={vi.fn()} />)
    const btn = screen.getByRole('button', { name: /\u5f00\u59cb\u521b\u5efa/i })
    await user.click(btn)
    expect(startSkill).toHaveBeenCalledWith('init')
  })

  // --- Error Case ---
  it('shows error message when startSkill fails', async () => {
    startSkill.mockRejectedValue(new Error('\u542f\u52a8\u5931\u8d25'))
    const user = userEvent.setup()
    render(<InitWizard onCompleted={vi.fn()} onCancelled={vi.fn()} />)
    const btn = screen.getByRole('button', { name: /\u5f00\u59cb\u521b\u5efa/i })
    await user.click(btn)
    await waitFor(() => {
      expect(screen.getByText(/\u542f\u52a8\u5931\u8d25/)).toBeInTheDocument()
    })
  })

  // --- Step 5: CreativityPackageSelector ---
  it('Step 5 renders package cards from stepState.output_data.packages', async () => {
    const packages = [
      { id: 'pkg1', name: '\u521b\u610f\u5305A', description: '\u63cf\u8ff7A', constraints: ['\u7ea6\u675f1'], score: { creativity: 4, feasibility: 3 } },
      { id: 'pkg2', name: '\u521b\u610f\u5305B', description: '\u63cf\u8ff7B', constraints: ['\u7ea6\u675f2'], score: { creativity: 5, feasibility: 4 } },
    ]
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    const CPS = InitWizardModule.CreativityPackageSelector
    render(<CPS stepState={{ output_data: { packages } }} onSubmit={onSubmit} />)

    expect(screen.getByText('\u521b\u610f\u5305A')).toBeInTheDocument()
    expect(screen.getByText('\u521b\u610f\u5305B')).toBeInTheDocument()

    const cards = screen.getAllByText(/\u521b\u610f\u5305/)
    expect(cards.length).toBeGreaterThanOrEqual(2)

    // Click first card
    await user.click(screen.getByText('\u521b\u610f\u5305A'))

    // Submit
    const submitBtn = screen.getByRole('button', { name: /\u786e\u8ba4\u9009\u62e9/i })
    await user.click(submitBtn)

    expect(onSubmit).toHaveBeenCalledWith({ selected_package_id: 'pkg1' })
  })

  it('Step 5 submit button is disabled when no package is selected', async () => {
    const packages = [
      { id: 'pkg1', name: '\u521b\u610f\u5305A', description: 'A', constraints: [], score: {} },
    ]

    const CPS = InitWizardModule.CreativityPackageSelector
    render(<CPS stepState={{ output_data: { packages } }} onSubmit={vi.fn()} />)

    const submitBtn = screen.getByRole('button', { name: /\u786e\u8ba4\u9009\u62e9/i })
    expect(submitBtn).toBeDisabled()
  })

  // --- Step 6: SummaryConfirmation ---
  it('Step 6 shows summary when gate_passed is true', () => {
    const summaryText = '\u8fd9\u662f\u4e00\u6bb5\u6545\u4e8b\u6458\u8981'
    const CPS = InitWizardModule.SummaryConfirmation
    render(<CPS stepState={{ output_data: { summary: summaryText, gate_passed: true } }} onSubmit={vi.fn()} />)

    expect(screen.getByText('\u9879\u76ee\u6458\u8981')).toBeInTheDocument()
    expect(screen.getByText(summaryText)).toBeInTheDocument()
  })

  it('Step 6 shows confirm button when gate_passed is true', async () => {
    const CPS = InitWizardModule.SummaryConfirmation
    const onSubmit = vi.fn()
    render(<CPS stepState={{ output_data: { summary: 'test', gate_passed: true } }} onSubmit={onSubmit} />)

    const btn = screen.getByRole('button', { name: /\u786e\u8ba4\u521b\u5efa/i })
    expect(btn).not.toBeDisabled()
  })

  it('Step 6 shows gate warning and missing items when gate_passed is false', () => {
    const missing = ['\u4e66\u540d\u672a\u586b', '\u4e16\u754c\u89c2\u672a\u5b9a']
    const CPS = InitWizardModule.SummaryConfirmation
    render(<CPS stepState={{ output_data: { gate_passed: false, missing_items: missing } }} onSubmit={vi.fn()} />)

    expect(screen.getByText('以下必填项尚未完成')).toBeInTheDocument()
    missing.forEach(item => {
      expect(screen.getByText(item)).toBeInTheDocument()
    })
  })

  it('Step 6 does NOT show confirm button when gate_passed is false', () => {
    const CPS = InitWizardModule.SummaryConfirmation
    render(<CPS stepState={{ output_data: { gate_passed: false, missing_items: ['\u9879'] } }} onSubmit={vi.fn()} />)

    expect(screen.queryByRole('button', { name: /\u786e\u8ba4\u521b\u5efa/i })).toBeNull()
  })
})
