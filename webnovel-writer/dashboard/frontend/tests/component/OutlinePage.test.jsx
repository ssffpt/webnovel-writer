import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock API
vi.mock('@/api.js', () => ({
  fetchOutlineTree: vi.fn(),
  readFile: vi.fn(),
  saveFile: vi.fn(),
}))

// Mock PlanFlow
vi.mock('@/workbench/PlanFlow.jsx', () => ({
  default: function MockPlanFlow({ onCompleted, onCancelled }) {
    return (
      <div data-testid="plan-flow">
        <button onClick={onCompleted}>完成</button>
        <button onClick={onCancelled}>取消</button>
      </div>
    )
  },
}))

import { fetchOutlineTree, readFile, saveFile } from '@/api.js'
import OutlinePage from '@/workbench/OutlinePage.jsx'

describe('OutlinePage', () => {
  const defaultProps = {
    loading: false,
    loadError: null,
    onRetry: vi.fn(),
    onContextChange: vi.fn(),
    onPageStateChange: vi.fn(),
    cachedSelectedPath: null,
    reloadToken: 0,
    onRunAction: vi.fn(),
    summary: { project: { path: '/test/project' } },
  }

  beforeEach(() => {
    vi.clearAllMocks()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '' })
    saveFile.mockResolvedValue({})
  })

  // --- Loading states ---
  it('renders loading spinner when loading is true', () => {
    render(<OutlinePage {...defaultProps} loading />)
    expect(screen.getByText('正在加载大纲工作区…')).toBeInTheDocument()
  })

  it('renders loading spinner during tree loading', async () => {
    fetchOutlineTree.mockImplementation(() => new Promise(() => {}))
    render(<OutlinePage {...defaultProps} />)
    expect(screen.getByText('正在加载大纲工作区…')).toBeInTheDocument()
  })

  // --- Error states ---
  it('renders error message when loadError is present', async () => {
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    render(<OutlinePage {...defaultProps} loadError="网络错误" />)
    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /重新加载/i })).toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    render(<OutlinePage {...defaultProps} loadError="网络错误" />)
    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument()
    })
    await user.click(screen.getByRole('button', { name: /重新加载/i }))
    expect(defaultProps.onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders tree error message when fetchOutlineTree fails', async () => {
    fetchOutlineTree.mockRejectedValue(new Error('大纲树加载失败'))
    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('大纲树加载失败')).toBeInTheDocument()
    })
  })

  // --- Normal rendering ---
  it('renders outline workspace with fixed nodes and volume list', async () => {
    fetchOutlineTree.mockResolvedValue({
      files: [],
      volumes: [
        { number: 1, has_outline: true, outline_path: '大纲/第1卷.md', chapter_range: [1, 30] },
        { number: 2, has_outline: false, chapter_range: [31, 60] },
      ],
      total_volumes: 2,
    })
    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('大纲结构')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /总纲/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /爽点规划/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /第1卷/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /生成第2卷大纲/i })).toBeInTheDocument()
    expect(screen.getByText('共 2 卷')).toBeInTheDocument()
  })

  it('auto-selects first fixed node when no cached path', async () => {
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '总纲内容' })
    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('大纲/总纲.md')
    })
    await waitFor(() => {
      expect(screen.getByDisplayValue('总纲内容')).toBeInTheDocument()
    })
  })

  it('auto-selects cached path if provided', async () => {
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '爽点内容' })
    render(<OutlinePage {...defaultProps} cachedSelectedPath="大纲/爽点规划.md" />)
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('大纲/爽点规划.md')
    })
  })

  // --- Interactions: tree selection ---
  it('switches file when tree item is clicked', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValueOnce({ content: '总纲内容' })
    readFile.mockResolvedValueOnce({ content: '爽点内容' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('总纲内容')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /爽点规划/i }))
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('大纲/爽点规划.md')
    })
  })

  // --- Interactions: dirty confirm dialog ---
  it('shows confirm dialog when switching file with unsaved changes', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValueOnce({ content: '总纲内容' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('总纲内容')).toBeInTheDocument())

    // Edit to make dirty
    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增内容')

    // Try switch
    await user.click(screen.getByRole('button', { name: /爽点规划/i }))
    expect(screen.getByText('存在未保存内容')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /继续/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /取消/i })).toBeInTheDocument()
  })

  it('confirms switch and changes file', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValueOnce({ content: '总纲内容' })
    readFile.mockResolvedValueOnce({ content: '爽点内容' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('总纲内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByRole('button', { name: /爽点规划/i }))

    await user.click(screen.getByRole('button', { name: /继续/i }))
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('大纲/爽点规划.md')
    })
  })

  it('cancels switch and keeps current file', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '总纲内容' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('总纲内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByRole('button', { name: /爽点规划/i }))

    await user.click(screen.getByRole('button', { name: /取消/i }))
    expect(screen.queryByText('存在未保存内容')).not.toBeInTheDocument()
    expect(screen.getByDisplayValue('总纲内容新增')).toBeInTheDocument()
  })

  // --- Interactions: save ---
  it('calls saveFile when save button is clicked', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '总纲内容' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('总纲内容')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '修改')
    await user.click(screen.getByRole('button', { name: /^保存$/i }))

    await waitFor(() => {
      expect(saveFile).toHaveBeenCalledWith('大纲/总纲.md', '总纲内容修改')
    })
  })

  it('shows saved badge after successful save', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '内容')
    await user.click(screen.getByRole('button', { name: /^保存$/i }))

    await waitFor(() => {
      expect(screen.getByText('已保存')).toBeInTheDocument()
    })
  })

  // --- PlanFlow ---
  it('shows PlanFlow when 生成卷纲 is clicked', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /生成卷纲/i }))
    expect(screen.getByTestId('plan-flow')).toBeInTheDocument()
  })

  it('closes PlanFlow when completed', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /生成卷纲/i }))
    expect(screen.getByTestId('plan-flow')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /完成/i }))
    expect(screen.queryByTestId('plan-flow')).not.toBeInTheDocument()
  })

  // --- Volume generate ---
  it('calls onRunAction when generating volume outline', async () => {
    const user = userEvent.setup()
    fetchOutlineTree.mockResolvedValue({
      files: [],
      volumes: [{ number: 2, has_outline: false, chapter_range: [31, 60] }],
      total_volumes: 1,
    })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /生成第2卷大纲/i })).toBeInTheDocument()
    })

    await user.click(screen.getByRole('button', { name: /生成第2卷大纲/i }))
    expect(defaultProps.onRunAction).toHaveBeenCalledWith({
      type: 'plan_outline',
      label: '生成第2卷大纲',
      params: { volume: 2 },
    })
  })

  // --- Context sync ---
  it('calls onContextChange and onPageStateChange after selection', async () => {
    fetchOutlineTree.mockResolvedValue({ files: [], volumes: [], total_volumes: 0 })
    readFile.mockResolvedValue({ content: '内容' })

    render(<OutlinePage {...defaultProps} />)
    await waitFor(() => {
      const calls = defaultProps.onContextChange.mock.calls
      const match = calls.find(c => c[0].selectedPath === '大纲/总纲.md')
      expect(match).toBeTruthy()
    })
  })
})
