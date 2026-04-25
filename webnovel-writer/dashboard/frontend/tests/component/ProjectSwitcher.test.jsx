import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock api.js
const mockRemoveProject = vi.fn()
const mockRenameProject = vi.fn()
const mockCleanupProjects = vi.fn()

vi.mock('@/api.js', () => ({
  removeProject: (...args) => mockRemoveProject(...args),
  renameProject: (...args) => mockRenameProject(...args),
  cleanupProjects: (...args) => mockCleanupProjects(...args),
}))

import ProjectSwitcher from '@/workbench/ProjectSwitcher.jsx'

describe('ProjectSwitcher', () => {
  const mockProjects = [
    { path: '/path/to/project1', name: '我的小说A', genre: '玄幻', current_chapter: 3 },
    { path: '/path/to/project2', name: '我的小说B', genre: '都市', current_chapter: 1 },
  ]

  const defaultProps = {
    projects: mockProjects,
    currentPath: '/path/to/project1',
    onSwitch: vi.fn(),
    onCreateNew: vi.fn(),
    onProjectsChange: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // Mock window.confirm to return true
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    // Mock window.alert
    vi.spyOn(window, 'alert').mockImplementation(() => {})
  })

  // --- Rendering ---
  it('renders project name when current project exists', () => {
    render(<ProjectSwitcher {...defaultProps} />)
    expect(screen.getByText('我的小说A')).toBeInTheDocument()
  })

  it('renders "选择项目" when no current project', () => {
    render(<ProjectSwitcher {...defaultProps} currentPath="/nonexistent" />)
    expect(screen.getByText('选择项目')).toBeInTheDocument()
  })

  it('shows dropdown when trigger is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    expect(screen.getByText('我的小说B')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /管理项目/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /\+ 创建新小说/i })).toBeInTheDocument()
  })

  it('hides dropdown when clicking outside', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    expect(screen.getByText('我的小说B')).toBeInTheDocument()
    // Click outside
    await user.click(document.body)
    expect(screen.queryByText('我的小说B')).not.toBeInTheDocument()
  })

  it('calls onSwitch with path when project item is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /我的小说B/ }))
    expect(defaultProps.onSwitch).toHaveBeenCalledWith('/path/to/project2')
  })

  it('closes dropdown after switching project', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /我的小说B/ }))
    expect(screen.queryByRole('button', { name: /我的小说B/ })).not.toBeInTheDocument()
  })

  it('calls onCreateNew when create button is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /\+ 创建新小说/i }))
    expect(defaultProps.onCreateNew).toHaveBeenCalledTimes(1)
  })

  // --- Management View ---
  it('enters management view when "管理项目" is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    expect(screen.getByText('项目管理')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /← 返回/i })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /重命名/i })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /移除/i })).toHaveLength(2)
    expect(screen.getAllByRole('button', { name: /删除/i })).toHaveLength(2)
    expect(screen.getByRole('button', { name: /清理无效记录/i })).toBeInTheDocument()
  })

  it('returns to list view when back button is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getByRole('button', { name: /← 返回/i }))
    expect(screen.queryByText('项目管理')).not.toBeInTheDocument()
    // Should show the list view with project items
    expect(screen.getByText('我的小说B')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /管理项目/i })).toBeInTheDocument()
  })

  // --- Rename ---
  it('shows rename input when rename button is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /重命名/i })[0])
    const input = screen.getByRole('textbox')
    expect(input).toHaveValue('我的小说A')
    expect(screen.getAllByRole('button', { name: /保存/i })[0]).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /取消/i })[0]).toBeInTheDocument()
  })

  it('calls renameProject API when save is clicked', async () => {
    const user = userEvent.setup()
    mockRenameProject.mockResolvedValue({})
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /重命名/i })[0])
    const input = screen.getByRole('textbox')
    await user.clear(input)
    await user.type(input, '新书名')
    await user.click(screen.getAllByRole('button', { name: /保存/i })[0])
    expect(mockRenameProject).toHaveBeenCalledWith('/path/to/project1', '新书名')
    expect(defaultProps.onProjectsChange).toHaveBeenCalled()
  })

  it('calls renameProject when Enter key is pressed', async () => {
    const user = userEvent.setup()
    mockRenameProject.mockResolvedValue({})
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /重命名/i })[0])
    const input = screen.getByRole('textbox')
    await user.clear(input)
    await user.type(input, '新书名按回车')
    await user.keyboard('{Enter}')
    expect(mockRenameProject).toHaveBeenCalledWith('/path/to/project1', '新书名按回车')
  })

  it('cancels rename without calling API when cancel is clicked', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /重命名/i })[0])
    await user.click(screen.getAllByRole('button', { name: /取消/i })[0])
    expect(mockRenameProject).not.toHaveBeenCalled()
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
  })

  it('does not rename when input is empty', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /重命名/i })[0])
    const input = screen.getByRole('textbox')
    await user.clear(input)
    await user.click(screen.getAllByRole('button', { name: /保存/i })[0])
    expect(mockRenameProject).not.toHaveBeenCalled()
  })

  it('shows alert when rename fails', async () => {
    const user = userEvent.setup()
    mockRenameProject.mockRejectedValue(new Error('重命名失败'))
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /重命名/i })[0])
    const input = screen.getByRole('textbox')
    await user.clear(input)
    await user.type(input, '新书名')
    await user.click(screen.getAllByRole('button', { name: /保存/i })[0])
    expect(window.alert).toHaveBeenCalledWith('重命名失败：重命名失败')
  })

  // --- Remove ---
  it('calls removeProject with deleteDir=false when 移除 is clicked', async () => {
    const user = userEvent.setup()
    mockRemoveProject.mockResolvedValue({})
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /移除/i })[0])
    expect(window.confirm).toHaveBeenCalledWith('确定要从列表移除项目「我的小说A」？')
    expect(mockRemoveProject).toHaveBeenCalledWith('/path/to/project1', false)
    expect(defaultProps.onProjectsChange).toHaveBeenCalled()
  })

  it('does not call removeProject when confirm is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /移除/i })[0])
    expect(mockRemoveProject).not.toHaveBeenCalled()
  })

  // --- Delete ---
  it('calls removeProject with deleteDir=true when 删除 is clicked', async () => {
    const user = userEvent.setup()
    mockRemoveProject.mockResolvedValue({})
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /删除/i })[0])
    expect(window.confirm).toHaveBeenCalledWith('确定要彻底删除项目「我的小说A」？')
    expect(mockRemoveProject).toHaveBeenCalledWith('/path/to/project1', true)
    expect(defaultProps.onProjectsChange).toHaveBeenCalled()
  })

  it('shows alert when remove/delete fails', async () => {
    const user = userEvent.setup()
    mockRemoveProject.mockRejectedValue(new Error('删除失败'))
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getAllByRole('button', { name: /删除/i })[0])
    expect(window.alert).toHaveBeenCalledWith('移除失败：删除失败')
  })

  // --- Cleanup ---
  it('calls cleanupProjects when cleanup button is clicked', async () => {
    const user = userEvent.setup()
    mockCleanupProjects.mockResolvedValue({ removed: ['/path/to/ghost1', '/path/to/ghost2'] })
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getByRole('button', { name: /清理无效记录/i }))
    expect(window.confirm).toHaveBeenCalledWith('清理已删除的项目记录？')
    expect(mockCleanupProjects).toHaveBeenCalled()
    expect(window.alert).toHaveBeenCalledWith('已清理 2 个无效记录')
    expect(defaultProps.onProjectsChange).toHaveBeenCalled()
  })

  it('does not show alert when cleanup removes 0 records', async () => {
    const user = userEvent.setup()
    mockCleanupProjects.mockResolvedValue({ removed: [] })
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getByRole('button', { name: /清理无效记录/i }))
    expect(window.alert).not.toHaveBeenCalled()
  })

  it('shows alert when cleanup fails', async () => {
    const user = userEvent.setup()
    mockCleanupProjects.mockRejectedValue(new Error('清理失败'))
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    await user.click(screen.getByRole('button', { name: /管理项目/i }))
    await user.click(screen.getByRole('button', { name: /清理无效记录/i }))
    expect(window.alert).toHaveBeenCalledWith('清理失败：清理失败')
  })

  // --- Empty state ---
  it('shows empty message when no projects', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} projects={[]} />)
    await user.click(screen.getByRole('button', { name: /选择项目/ }))
    expect(screen.getByText('暂无项目')).toBeInTheDocument()
  })

  // --- Rendering project meta info ---
  it('renders project genre and chapter info', async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher {...defaultProps} />)
    await user.click(screen.getByRole('button', { name: /我的小说A/ }))
    const item = screen.getByText(/玄幻.*·.*第3章/)
    expect(item).toBeInTheDocument()
  })
})
