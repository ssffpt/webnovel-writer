import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock API
vi.mock('@/api.js', () => ({
  fetchFileTree: vi.fn(),
  readFile: vi.fn(),
  saveFile: vi.fn(),
}))

// Mock child components
vi.mock('@/workbench/WriteFlow.jsx', () => ({
  default: function MockWriteFlow({ onCompleted, onCancelled }) {
    return (
      <div data-testid="write-flow">
        <button onClick={() => onCompleted('AI生成内容')}>完成创作</button>
        <button onClick={onCancelled}>取消</button>
      </div>
    )
  },
}))

vi.mock('@/workbench/ReviewFlow.jsx', () => ({
  default: function MockReviewFlow({ onCompleted, onCancelled }) {
    return (
      <div data-testid="review-flow">
        <button onClick={onCompleted}>完成审查</button>
        <button onClick={onCancelled}>取消</button>
      </div>
    )
  },
}))

import { fetchFileTree, readFile, saveFile } from '@/api.js'
import ChapterPage from '@/workbench/ChapterPage.jsx'

describe('ChapterPage', () => {
  const defaultProps = {
    loading: false,
    loadError: null,
    onRetry: vi.fn(),
    onContextChange: vi.fn(),
    onPageStateChange: vi.fn(),
    cachedSelectedPath: null,
    reloadToken: 0,
    onFocusModeChange: vi.fn(),
  }

  const mockTree = {
    正文: [
      { type: 'file', name: '第1章.md', path: 'project/正文/第1章.md', size: 1200 },
      { type: 'file', name: '第2章.md', path: 'project/正文/第2章.md', size: 2500 },
      { type: 'file', name: '第3章.md', path: 'project/正文/第3章.md', size: 1800 },
    ],
  }

  beforeEach(() => {
    vi.clearAllMocks()
    fetchFileTree.mockResolvedValue(mockTree)
    readFile.mockResolvedValue({ content: '' })
    saveFile.mockResolvedValue({})
  })

  // --- Loading ---
  it('renders loading when loading is true', () => {
    render(<ChapterPage {...defaultProps} loading />)
    expect(screen.getByText('正在加载章节工作区…')).toBeInTheDocument()
  })

  it('renders loading during tree loading', async () => {
    fetchFileTree.mockImplementation(() => new Promise(() => {}))
    render(<ChapterPage {...defaultProps} />)
    expect(screen.getByText('正在加载章节工作区…')).toBeInTheDocument()
  })

  // --- Error ---
  it('renders error when loadError is present', async () => {
    fetchFileTree.mockResolvedValue(mockTree)
    render(<ChapterPage {...defaultProps} loadError="网络错误" />)
    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /重新加载摘要/i })).toBeInTheDocument()
  })

  it('calls onRetry when retry button clicked', async () => {
    const user = userEvent.setup()
    fetchFileTree.mockResolvedValue(mockTree)
    render(<ChapterPage {...defaultProps} loadError="网络错误" />)
    await waitFor(() => expect(screen.getByText('网络错误')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: /重新加载摘要/i }))
    expect(defaultProps.onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders tree error when fetchFileTree fails', async () => {
    fetchFileTree.mockRejectedValue(new Error('章节列表加载失败'))
    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('章节列表加载失败')).toBeInTheDocument()
    })
  })

  // --- Empty state ---
  it('renders empty state when no chapters', async () => {
    fetchFileTree.mockResolvedValue({ 正文: [] })
    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('还没有章节')).toBeInTheDocument()
    })
    expect(screen.getByText('开始写第1章吧！')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /写第1章/i })).toBeInTheDocument()
  })

  // --- Normal rendering ---
  it('renders chapter list in reverse order', async () => {
    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('第3章.md')).toBeInTheDocument()
    })
    const buttons = screen.getAllByRole('button')
    // Chapter buttons should appear in reverse: 3, 2, 1
    const chapterButtons = buttons.filter(b => b.textContent.includes('第') && b.textContent.includes('章'))
    expect(chapterButtons[0].textContent).toContain('第3章')
    expect(chapterButtons[1].textContent).toContain('第2章')
    expect(chapterButtons[2].textContent).toContain('第1章')
  })

  it('auto-selects first chapter when no cached path', async () => {
    readFile.mockResolvedValue({ content: '第一章内容' })
    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('project/正文/第1章.md')
    })
    await waitFor(() => {
      expect(screen.getByDisplayValue('第一章内容')).toBeInTheDocument()
    })
  })

  it('auto-selects cached path if exists in tree', async () => {
    readFile.mockResolvedValue({ content: '第三章内容' })
    render(<ChapterPage {...defaultProps} cachedSelectedPath="project/正文/第3章.md" />)
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('project/正文/第3章.md')
    })
  })

  // --- Interactions: chapter selection ---
  it('switches chapter when list item clicked', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValueOnce({ content: '第一章内容' })
    readFile.mockResolvedValueOnce({ content: '第二章内容' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('第一章内容')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /第2章/i }))
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('project/正文/第2章.md')
    })
  })

  // --- Dirty confirm ---
  it('shows confirm dialog when switching with unsaved changes', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '第一章内容' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('第一章内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByRole('button', { name: /第2章/i }))

    expect(screen.getByText('存在未保存内容')).toBeInTheDocument()
  })

  it('confirms switch and changes chapter', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValueOnce({ content: '第一章内容' })
    readFile.mockResolvedValueOnce({ content: '第二章内容' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('第一章内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByRole('button', { name: /第2章/i }))
    await user.click(screen.getByRole('button', { name: /^继续$/i }))

    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('project/正文/第2章.md')
    })
  })

  it('cancels switch and keeps current content', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '第一章内容' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('第一章内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByRole('button', { name: /第2章/i }))
    await user.click(screen.getByRole('button', { name: /^取消$/i }))

    expect(screen.queryByText('存在未保存内容')).not.toBeInTheDocument()
    expect(screen.getByDisplayValue('第一章内容新增')).toBeInTheDocument()
  })

  // --- Save ---
  it('calls saveFile when save button clicked', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '第一章内容' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('第一章内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '修改')
    await user.click(screen.getByRole('button', { name: /^保存$/i }))

    await waitFor(() => {
      expect(saveFile).toHaveBeenCalledWith('project/正文/第1章.md', '第一章内容修改')
    })
  })

  it('shows saved badge after save', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '内容')
    await user.click(screen.getByRole('button', { name: /^保存$/i }))

    await waitFor(() => {
      expect(screen.getByText('已保存')).toBeInTheDocument()
    })
  })

  // --- Focus mode ---
  it('toggles focus mode when focus button clicked', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    const focusBtn = screen.getByRole('button', { name: /专注/i })
    await user.click(focusBtn)
    expect(defaultProps.onFocusModeChange).toHaveBeenCalledWith(true)

    // Exit focus mode
    const exitBtn = screen.getByRole('button', { name: /退出专注/i })
    await user.click(exitBtn)
    expect(defaultProps.onFocusModeChange).toHaveBeenCalledWith(false)
  })

  // --- Sidebar collapse ---
  it('toggles sidebar collapse', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('章节')).toBeInTheDocument())

    const collapseBtn = screen.getByTitle('收起侧栏')
    await user.click(collapseBtn)

    const expandBtn = screen.getByTitle('展开侧栏')
    expect(expandBtn).toBeInTheDocument()
  })

  // --- Edit mode: AI ---
  it('switches to AI创作 mode and shows WriteFlow', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /AI 创作/i }))
    expect(screen.getByTestId('write-flow')).toBeInTheDocument()
  })

  it('returns to manual mode when WriteFlow completes', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /AI 创作/i }))
    expect(screen.getByTestId('write-flow')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /完成创作/i }))
    expect(screen.queryByTestId('write-flow')).not.toBeInTheDocument()
    expect(screen.getByDisplayValue('AI生成内容')).toBeInTheDocument()
  })

  // --- Review ---
  it('opens review panel when 审查本章 clicked', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '章节内容' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('章节内容')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /审查本章/i }))
    expect(screen.getByTestId('review-flow')).toBeInTheDocument()
  })

  it('closes review panel when completed', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /审查本章/i }))
    expect(screen.getByTestId('review-flow')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /完成审查/i }))
    expect(screen.queryByTestId('review-flow')).not.toBeInTheDocument()
  })

  // --- Word count ---
  it('shows word count in status bar', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '这是正文内容')
    expect(screen.getByText('6 字')).toBeInTheDocument()
  })

  // --- Context sync ---
  it('calls onContextChange with correct page and path', async () => {
    readFile.mockResolvedValue({ content: '内容' })
    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => {
      const calls = defaultProps.onContextChange.mock.calls
      const match = calls.find(c => c[0].selectedPath === 'project/正文/第1章.md')
      expect(match).toBeTruthy()
    })
  })

  // --- Next chapter button ---
  it('shows 写第N章 button with next chapter number', async () => {
    render(<ChapterPage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /写第4章/i })).toBeInTheDocument()
    })
  })
})
