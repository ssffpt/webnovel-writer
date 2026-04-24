import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock dependencies
vi.mock('@/api.js', () => ({
  startSkill: vi.fn(),
}))

vi.mock('@/workbench/SkillFlowPanel.jsx', () => ({
  default: function MockSkillFlowPanel({ skillId }) {
    return <div data-testid="skill-flow-panel" data-skill-id={skillId} />
  },
}))

vi.mock('@/workbench/InitWizard.jsx', () => ({
  default: function MockInitWizard({ onCompleted, onCancelled }) {
    return (
      <div data-testid="init-wizard">
        <button onClick={onCompleted}>完成</button>
        <button onClick={onCancelled}>取消</button>
      </div>
    )
  },
}))

vi.mock('@/workbench/RAGConfig.jsx', () => ({
  default: function MockRAGConfig({ ...props }) {
    return <div data-testid="rag-config" {...props}>RAG Config</div>
  },
}))

import OverviewPage from '@/workbench/OverviewPage.jsx'

describe('OverviewPage', () => {
  const defaultProps = {
    summary: null,
    loading: false,
    loadError: null,
    onRetry: vi.fn(),
    projectStatus: 'no-project',
    projectInfo: null,
    recentActivities: [],
    onCreateNew: vi.fn(),
    showWizard: false,
    onWizardClosed: vi.fn(),
    onWizardCompleted: vi.fn(),
    onNavigateToPage: vi.fn(),
    onRunAction: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  // --- State: Loading ---
  it('renders loading spinner when loading is true', () => {
    render(<OverviewPage {...defaultProps} loading />)
    expect(screen.getByText('正在加载项目信息…')).toBeInTheDocument()
  })

  it('renders loading spinner when projectStatus is loading', () => {
    render(<OverviewPage {...defaultProps} projectStatus="loading" />)
    expect(screen.getByText('正在加载项目信息…')).toBeInTheDocument()
  })

  // --- State: Error ---
  it('renders error message and retry button when loadError is present', () => {
    render(<OverviewPage {...defaultProps} loadError="网络请求失败" />)
    expect(screen.getByText('网络请求失败')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /重新加载/i })).toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    render(<OverviewPage {...defaultProps} loadError="网络请求失败" />)
    const btn = screen.getByRole('button', { name: /重新加载/i })
    await user.click(btn)
    expect(defaultProps.onRetry).toHaveBeenCalledTimes(1)
  })

  // --- State: showWizard ---
  it('renders InitWizard when showWizard is true', () => {
    render(<OverviewPage {...defaultProps} showWizard />)
    expect(screen.getByTestId('init-wizard')).toBeInTheDocument()
  })

  it('calls onWizardCompleted when wizard finish button is clicked', async () => {
    const user = userEvent.setup()
    render(<OverviewPage {...defaultProps} showWizard />)
    const btn = screen.getByRole('button', { name: /完成/i })
    await user.click(btn)
    expect(defaultProps.onWizardCompleted).toHaveBeenCalledTimes(1)
  })

  // --- State: no-project ---
  it('renders empty state when projectStatus is no-project', () => {
    render(<OverviewPage {...defaultProps} />)
    expect(screen.getByText('欢迎使用网文创作工作台')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /创建新小说/i })).toBeInTheDocument()
  })

  it('calls onCreateNew when create button is clicked in empty state', async () => {
    const user = userEvent.setup()
    render(<OverviewPage {...defaultProps} />)
    const btn = screen.getByRole('button', { name: /创建新小说/i })
    await user.click(btn)
    expect(defaultProps.onCreateNew).toHaveBeenCalledTimes(1)
  })

  // --- State: incomplete ---
  it('renders incomplete state with project info', () => {
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="incomplete"
        summary={{ project: { title: '测试书名' }, progress: { current_chapter: 0 } }}
      />
    )
    expect(screen.getByText('总览')).toBeInTheDocument()
    expect(screen.getByText('书名：测试书名')).toBeInTheDocument()
    expect(screen.getByText('项目设置尚未完成')).toBeInTheDocument()
  })

  it('calls onCreateNew when continue setup button is clicked in incomplete state', async () => {
    const user = userEvent.setup()
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="incomplete"
        summary={{ project: { title: '测试书名' } }}
      />
    )
    const btn = screen.getByRole('button', { name: /继续设置/i })
    await user.click(btn)
    expect(defaultProps.onCreateNew).toHaveBeenCalledTimes(1)
  })

  // --- State: ready (core) ---
  it('renders ready state with project overview and no activities', () => {
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{
          project: { title: '我的小说', genre: '玄幻' },
          progress: { current_chapter: 0 },
        }}
      />
    )
    expect(screen.getByText('书名：我的小说')).toBeInTheDocument()
    expect(screen.getByText('题材：玄幻')).toBeInTheDocument()
    expect(screen.getByText('当前章节：—')).toBeInTheDocument()
    expect(screen.getByText('暂无最近动态。')).toBeInTheDocument()
  })

  it('renders total words when progress has total_words', () => {
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{
          project: { title: '我的小说' },
          progress: { current_chapter: 3, total_words: 12345 },
        }}
      />
    )
    expect(screen.getByText('总字数：12,345')).toBeInTheDocument()
  })

  it('renders recent activities list', () => {
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 1 } }}
        recentActivities={[
          { time: '10:00', message: '完成第1章写作' },
          { time: '09:30', message: '创建项目' },
        ]}
      />
    )
    expect(screen.getByText('完成第1章写作')).toBeInTheDocument()
    expect(screen.getByText('创建项目')).toBeInTheDocument()
  })

  it('limits recent activities to 5 items', () => {
    const activities = Array.from({ length: 7 }, (_, i) => ({
      time: `${i}:00`,
      message: `活动 ${i + 1}`,
    }))
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 1 } }}
        recentActivities={activities}
      />
    )
    const list = screen.getAllByText(/活动 \d/)
    expect(list).toHaveLength(5)
  })

  // --- Step Progress Bar ---
  it('shows writing step as pending when current_chapter is 0', () => {
    const { container } = render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 0 } }}
      />
    )
    const items = container.querySelectorAll('.step-progress-item')
    expect(items[0].classList.contains('completed')).toBe(true) // 起步
    expect(items[1].classList.contains('active')).toBe(false)   // 写作中
    expect(items[2].classList.contains('active')).toBe(false)   // 审查
  })

  it('shows writing step as active when current_chapter > 0', () => {
    const { container } = render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 2 } }}
      />
    )
    const items = container.querySelectorAll('.step-progress-item')
    expect(items[0].classList.contains('completed')).toBe(true) // 起步
    expect(items[1].classList.contains('active')).toBe(true)    // 写作中
    expect(items[2].classList.contains('active')).toBe(false)   // 审查
  })

  // --- Next Suggestion ---
  it('shows "开始写第1章" suggestion when current_chapter is 0', () => {
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 0 } }}
      />
    )
    expect(screen.getByText('下一步')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /开始写第1章/i })).toBeInTheDocument()
  })

  it('shows "写第N章" suggestion when current_chapter > 0', () => {
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 3 } }}
      />
    )
    expect(screen.getByRole('button', { name: /写第4章/i })).toBeInTheDocument()
  })

  it('calls onRunAction and onNavigateToPage when suggestion button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 2 } }}
      />
    )
    const btn = screen.getByRole('button', { name: /写第3章/i })
    await user.click(btn)
    expect(defaultProps.onRunAction).toHaveBeenCalledWith({
      type: 'write_chapter',
      label: '写第3章',
      chapter: 3,
    })
    expect(defaultProps.onNavigateToPage).toHaveBeenCalledWith('chapters')
  })

  // --- RAG Config ---
  it('toggles RAG config panel when RAG button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <OverviewPage
        {...defaultProps}
        projectStatus="ready"
        summary={{ project: { title: '我的小说' }, progress: { current_chapter: 1 } }}
      />
    )
    expect(screen.queryByTestId('rag-config')).not.toBeInTheDocument()
    const btn = screen.getByRole('button', { name: /RAG 向量检索/i })
    await user.click(btn)
    expect(screen.getByTestId('rag-config')).toBeInTheDocument()
  })

  // --- Default state ---
  it('renders empty state for unknown projectStatus', () => {
    render(<OverviewPage {...defaultProps} projectStatus="unknown" />)
    expect(screen.getByText('欢迎使用网文创作工作台')).toBeInTheDocument()
  })
})
