import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'

// Mock API
vi.mock('@/api.js', () => ({
  fetchJSON: vi.fn(),
  readFile: vi.fn(),
  saveFile: vi.fn(),
}))

import { fetchJSON, readFile, saveFile } from '@/api.js'
import SettingPage from '@/workbench/SettingPage.jsx'

describe('SettingPage', () => {
  const defaultProps = {
    loading: false,
    loadError: null,
    onRetry: vi.fn(),
    onContextChange: vi.fn(),
    onPageStateChange: vi.fn(),
    cachedSelectedPath: null,
    reloadToken: 0,
  }

  const mockEntities = [
    { id: 1, type: '角色', canonical_name: '张三', desc: '主角', file_path: '设定/人物/张三.md' },
    { id: 2, type: '势力', canonical_name: '天门宗', desc: '反派势力', file_path: '设定/势力/天门宗.md' },
    { id: 3, type: '地点', canonical_name: '青云山', desc: '修炼圣地', file_path: '设定/地点/青云山.md' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    fetchJSON.mockImplementation((path) => {
      if (path === '/api/entities') return Promise.resolve({ entities: mockEntities })
      if (path === '/api/query/foreshadowing') return Promise.resolve({ stats: {}, foreshadowing: [], by_tier: {} })
      if (path === '/api/query/golden-finger') return Promise.resolve({ golden_finger: null })
      if (path === '/api/query/rhythm') return Promise.resolve({ rhythm_data: {} })
      if (path === '/api/query/debt') return Promise.resolve({ debt_summary: null })
      return Promise.resolve({})
    })
    readFile.mockResolvedValue({ content: '' })
    saveFile.mockResolvedValue({})
  })

  // --- Loading states ---
  it('renders loading text when loading is true', () => {
    render(<SettingPage {...defaultProps} loading />)
    expect(screen.getByText('正在加载设定工作区…')).toBeInTheDocument()
  })

  it('renders loading text during entities loading', async () => {
    fetchJSON.mockImplementation(() => new Promise(() => {}))
    render(<SettingPage {...defaultProps} />)
    expect(screen.getByText('正在加载设定工作区…')).toBeInTheDocument()
  })

  // --- Error states ---
  it('renders error message when loadError is present', () => {
    render(<SettingPage {...defaultProps} loadError="网络错误" />)
    expect(screen.getByText('网络错误')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /重新加载/i })).toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    render(<SettingPage {...defaultProps} loadError="网络错误" />)
    await user.click(screen.getByRole('button', { name: /重新加载/i }))
    expect(defaultProps.onRetry).toHaveBeenCalledTimes(1)
  })

  it('renders entities error when fetch fails', async () => {
    fetchJSON.mockRejectedValue(new Error('实体加载失败'))
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('实体加载失败')).toBeInTheDocument()
    })
  })

  // --- Normal rendering ---
  it('renders category filters and entity list', async () => {
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => {
      expect(screen.getByText('实体分类')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: /全部\(3\)/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /人物\(1\)/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /势力\(1\)/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /地点\(1\)/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /张三/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /天门宗/i })).toBeInTheDocument()
  })

  it('auto-selects first entity on load', async () => {
    readFile.mockResolvedValue({ content: '张三的设定' })
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('设定/人物/张三.md')
    })
    await waitFor(() => {
      expect(screen.getByDisplayValue('张三的设定')).toBeInTheDocument()
    })
  })

  it('auto-selects entity matching cachedSelectedPath', async () => {
    readFile.mockResolvedValue({ content: '天门宗设定' })
    render(<SettingPage {...defaultProps} cachedSelectedPath="设定/势力/天门宗.md" />)
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('设定/势力/天门宗.md')
    })
  })

  // --- Category filter ---
  it('filters entities by category', async () => {
    const user = userEvent.setup()
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /张三/i })).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /势力\(1\)/i }))
    expect(screen.queryByRole('button', { name: /张三/i })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /天门宗/i })).toBeInTheDocument()
  })

  it('shows empty text when category has no entities', async () => {
    const user = userEvent.setup()
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('button', { name: /张三/i })).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /招式/i }))
    expect(screen.getByText('当前分类下暂无实体。')).toBeInTheDocument()
  })

  // --- Entity selection ---
  it('loads content when entity is clicked', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValueOnce({ content: '张三设定' })
    readFile.mockResolvedValueOnce({ content: '青云山设定' })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('张三设定')).toBeInTheDocument())

    await user.click(screen.getByText('青云山'))
    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('设定/地点/青云山.md')
    })
  })

  // --- Dirty confirm dialog ---
  it('shows confirm dialog when switching entity with unsaved changes', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '张三设定' })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('张三设定')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByText('天门宗'))

    expect(screen.getByText('存在未保存内容')).toBeInTheDocument()
  })

  it('confirms entity switch and loads new content', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValueOnce({ content: '张三设定' })
    readFile.mockResolvedValueOnce({ content: '天门宗设定' })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('张三设定')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByText('天门宗'))
    await user.click(screen.getByRole('button', { name: /继续/i }))

    await waitFor(() => {
      expect(readFile).toHaveBeenCalledWith('设定/势力/天门宗.md')
    })
  })

  it('cancels entity switch and keeps current content', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '张三设定' })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('张三设定')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '新增')
    await user.click(screen.getByText('天门宗'))
    await user.click(screen.getByRole('button', { name: /取消/i }))

    expect(screen.queryByText('存在未保存内容')).not.toBeInTheDocument()
    expect(screen.getByDisplayValue('张三设定新增')).toBeInTheDocument()
  })

  // --- Save ---
  it('calls saveFile when save button is clicked', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '张三设定' })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByDisplayValue('张三设定')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '修改')
    await user.click(screen.getByRole('button', { name: /^保存$/i }))

    await waitFor(() => {
      expect(saveFile).toHaveBeenCalledWith('设定/人物/张三.md', '张三设定修改')
    })
  })

  it('shows saved badge after successful save', async () => {
    const user = userEvent.setup()
    readFile.mockResolvedValue({ content: '' })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByRole('textbox')).toBeInTheDocument())

    const textarea = screen.getByRole('textbox')
    await user.type(textarea, '内容')
    await user.click(screen.getByRole('button', { name: /^保存$/i }))

    await waitFor(() => {
      expect(screen.getByText('已保存')).toBeInTheDocument()
    })
  })

  // --- Query tabs ---
  it('switches to foreshadowing tab', async () => {
    const user = userEvent.setup()
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('实体分类')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /^伏笔$/i }))
    await waitFor(() => {
      expect(fetchJSON).toHaveBeenCalledWith('/api/query/foreshadowing')
    })
    expect(screen.getByText('伏笔查询')).toBeInTheDocument()
  })

  it('switches to golden-finger tab', async () => {
    const user = userEvent.setup()
    fetchJSON.mockImplementation((path) => {
      if (path === '/api/entities') return Promise.resolve({ entities: mockEntities })
      if (path === '/api/query/golden-finger') {
        return Promise.resolve({
          golden_finger: { name: '系统', type: '辅助', level: 3, max_level: 10, progress_percent: 30 },
        })
      }
      return Promise.resolve({})
    })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('实体分类')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /^金手指$/i }))
    await waitFor(() => {
      expect(fetchJSON).toHaveBeenCalledWith('/api/query/golden-finger')
    })
    expect(screen.getByText('金手指状态')).toBeInTheDocument()
  })

  it('switches to rhythm tab', async () => {
    const user = userEvent.setup()
    fetchJSON.mockImplementation((path) => {
      if (path === '/api/entities') return Promise.resolve({ entities: mockEntities })
      if (path === '/api/query/rhythm') {
        return Promise.resolve({
          rhythm_data: {
            volume_1: { total_chapters: 10, pacing_score: 8, pacing_label: '快节奏', beat_distribution: { action: 5 }, emotion_curve: [], climax_chapters: [5] },
          },
        })
      }
      return Promise.resolve({})
    })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('实体分类')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /^节奏$/i }))
    await waitFor(() => {
      expect(fetchJSON).toHaveBeenCalledWith('/api/query/rhythm')
    })
    expect(screen.getByText('节奏分析')).toBeInTheDocument()
  })

  it('switches to debt tab', async () => {
    const user = userEvent.setup()
    fetchJSON.mockImplementation((path) => {
      if (path === '/api/entities') return Promise.resolve({ entities: mockEntities })
      if (path === '/api/query/debt') {
        return Promise.resolve({
          debt_summary: {
            total_unresolved: 2,
            total_resolved: 1,
            resolution_rate: 33,
            critical_debts: [],
            recently_resolved: [],
          },
        })
      }
      return Promise.resolve({})
    })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('实体分类')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /^债务$/i }))
    await waitFor(() => {
      expect(fetchJSON).toHaveBeenCalledWith('/api/query/debt')
    })
    expect(screen.getByText('债务查询')).toBeInTheDocument()
  })

  // --- Query tab error ---
  it('shows error in query tab when fetch fails', async () => {
    const user = userEvent.setup()
    fetchJSON.mockImplementation((path) => {
      if (path === '/api/entities') return Promise.resolve({ entities: mockEntities })
      if (path === '/api/query/foreshadowing') return Promise.reject(new Error('查询失败'))
      return Promise.resolve({})
    })

    render(<SettingPage {...defaultProps} />)
    await waitFor(() => expect(screen.getByText('实体分类')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: /^伏笔$/i }))
    await waitFor(() => {
      expect(screen.getByText('查询失败')).toBeInTheDocument()
    })
  })

  // --- Context sync ---
  it('calls onContextChange with correct page and path', async () => {
    readFile.mockResolvedValue({ content: '内容' })
    render(<SettingPage {...defaultProps} />)
    await waitFor(() => {
      const calls = defaultProps.onContextChange.mock.calls
      const match = calls.find(c => c[0].selectedPath === '设定/人物/张三.md')
      expect(match).toBeTruthy()
    })
  })
})
