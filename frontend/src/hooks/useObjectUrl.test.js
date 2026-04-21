import { describe, it, expect, vi, beforeEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useDerivedObjectUrl, useManagedObjectUrl } from './useObjectUrl'

describe('useDerivedObjectUrl', () => {
  beforeEach(() => {
    let n = 0
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => `blob:derived-${++n}`)
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  it('returns null when source is null', () => {
    const { result } = renderHook(({ src }) => useDerivedObjectUrl(src), {
      initialProps: { src: null },
    })
    expect(result.current).toBe(null)
  })

  it('creates a URL from a Blob', () => {
    const blob = new Blob(['x'], { type: 'text/plain' })
    const { result } = renderHook(() => useDerivedObjectUrl(blob))
    expect(result.current).toMatch(/^blob:derived-/)
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob)
  })

  it('revokes the previous URL when source changes', () => {
    const blob1 = new Blob(['1'])
    const blob2 = new Blob(['2'])
    const { result, rerender } = renderHook(({ src }) => useDerivedObjectUrl(src), {
      initialProps: { src: blob1 },
    })
    const firstUrl = result.current
    rerender({ src: blob2 })
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(firstUrl)
    expect(result.current).not.toBe(firstUrl)
  })

  it('revokes on unmount', () => {
    const blob = new Blob(['x'])
    const { result, unmount } = renderHook(() => useDerivedObjectUrl(blob))
    const url = result.current
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith(url)
  })
})

describe('useManagedObjectUrl', () => {
  beforeEach(() => {
    vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})
  })

  it('revokes the previous URL when a new one is set', () => {
    const { result } = renderHook(() => useManagedObjectUrl())
    const [, setUrl] = result.current
    act(() => { setUrl('blob:a') })
    act(() => { setUrl('blob:b') })
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:a')
  })

  it('revokes on unmount', () => {
    const { result, unmount } = renderHook(() => useManagedObjectUrl())
    act(() => { result.current[1]('blob:final') })
    unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:final')
  })
})
