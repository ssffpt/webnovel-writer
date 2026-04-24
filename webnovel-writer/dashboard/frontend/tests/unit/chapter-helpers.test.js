import { describe, it, expect } from 'vitest'
import { flattenFiles, extractChapterNumber } from '@/workbench/data.js'

// --- flattenFiles ---

describe('flattenFiles', () => {
  it('returns empty array for empty input', () => {
    expect(flattenFiles([])).toEqual([])
  })

  it('throws TypeError when null is passed (null not iterable)', () => {
    // undefined triggers default = [], null does not → throws
    expect(() => flattenFiles(null)).toThrow(TypeError)
  })

  it('returns [] for missing children in dir nodes', () => {
    const nodes = [{ type: 'dir', children: null }]
    expect(flattenFiles(nodes)).toEqual([])
  })

  it('extracts files from a flat file list', () => {
    const nodes = [
      { type: 'file', name: '第1章.md', path: '/chapters/第1章.md' },
      { type: 'file', name: '第2章.md', path: '/chapters/第2章.md' },
    ]
    expect(flattenFiles(nodes)).toEqual(nodes)
  })

  it('recursively flattens nested directories', () => {
    const nodes = [
      {
        type: 'dir',
        name: '正文',
        children: [
          { type: 'file', name: '第1章.md', path: '/chapters/第1章.md' },
          {
            type: 'dir',
            name: '子目录',
            children: [
              { type: 'file', name: '第10章.md', path: '/chapters/第10章.md' },
            ],
          },
        ],
      },
    ]
    const result = flattenFiles(nodes)
    expect(result).toHaveLength(2)
    expect(result[0].name).toBe('第1章.md')
    expect(result[1].name).toBe('第10章.md')
  })

  it('skips nodes without type file or dir', () => {
    const nodes = [
      { type: 'file', name: '第1章.md' },
      { type: 'unknown', name: '其他' },
      { type: 'dir', children: [{ type: 'file', name: '第2章.md' }] },
    ]
    const result = flattenFiles(nodes)
    expect(result).toHaveLength(2)
  })

  it('handles dir with no children', () => {
    const nodes = [{ type: 'dir', children: [] }]
    expect(flattenFiles(nodes)).toEqual([])
  })
})

// --- extractChapterNumber ---

describe('extractChapterNumber', () => {
  it('extracts number from chapter file name', () => {
    expect(extractChapterNumber('第1章.md')).toBe(1)
    expect(extractChapterNumber('第12章.txt')).toBe(12)
    expect(extractChapterNumber('第100章')).toBe(100)
  })

  it('returns null when no number in file name', () => {
    expect(extractChapterNumber('章节.md')).toBe(null)
    expect(extractChapterNumber('总纲.md')).toBe(null)
    expect(extractChapterNumber('')).toBe(null)
  })

  it('returns null for null/undefined/empty string', () => {
    expect(extractChapterNumber(null)).toBe(null)
    expect(extractChapterNumber(undefined)).toBe(null)
    expect(extractChapterNumber('')).toBe(null)
  })

  it('converts numeric input to string then extracts number', () => {
    // String(123) = "123" → match[1] = "123" → Number("123") = 123
    expect(extractChapterNumber(123)).toBe(123)
  })

  it('extracts first number when multiple numbers present', () => {
    expect(extractChapterNumber('第1章-草稿2.md')).toBe(1)
  })

  it('coerces string numbers to Number type', () => {
    expect(typeof extractChapterNumber('第5章.md')).toBe('number')
    expect(extractChapterNumber('第5章.md')).toBe(5)
  })
})
