import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import useAsyncSubmit from './useAsyncSubmit'

describe('useAsyncSubmit', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'] })
  })
  afterEach(() => {
    act(() => {
      vi.runOnlyPendingTimers()
    })
    vi.useRealTimers()
  })

  it('runs apiCall and invokes onSuccess with the result', async () => {
    const apiCall = vi.fn().mockResolvedValue({ value: 42 })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useAsyncSubmit())

    await act(async () => {
      await result.current.execute(apiCall, { onSuccess })
    })

    expect(apiCall).toHaveBeenCalledOnce()
    expect(onSuccess).toHaveBeenCalledWith({ value: 42 })
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBe('')
  })

  it('invokes onError with the error and sets error message via default handler', async () => {
    const apiErr = new Error('boom')
    const apiCall = vi.fn().mockRejectedValue(apiErr)

    const { result } = renderHook(() => useAsyncSubmit())

    await act(async () => {
      await result.current.execute(apiCall)
    })

    expect(result.current.error).toBe('boom')
    expect(result.current.loading).toBe(false)
    expect(result.current.phase).toBe(null)
  })

  it('onError override suppresses default setError', async () => {
    const apiCall = vi.fn().mockRejectedValue(new Error('x'))
    const onError = vi.fn()

    const { result } = renderHook(() => useAsyncSubmit())

    await act(async () => {
      await result.current.execute(apiCall, { onError })
    })

    expect(onError).toHaveBeenCalledOnce()
    expect(result.current.error).toBe('')
  })

  it('aborts the previous in-flight call when execute is invoked again', async () => {
    let firstSignal
    const firstCall = vi.fn((signal) => {
      firstSignal = signal
      return new Promise((_, reject) => {
        signal.addEventListener('abort', () => {
          reject(new DOMException('Aborted', 'AbortError'))
        }, { once: true })
      })
    })
    const secondCall = vi.fn().mockResolvedValue({ ok: true })

    const { result } = renderHook(() => useAsyncSubmit())

    act(() => { result.current.execute(firstCall) })
    await act(async () => {
      await result.current.execute(secondCall)
    })

    expect(firstSignal?.aborted).toBe(true)
    expect(secondCall).toHaveBeenCalledOnce()
  })

  it('reset clears loading, phase, progress and error', async () => {
    const apiCall = vi.fn().mockRejectedValue(new Error('fail'))
    const { result } = renderHook(() => useAsyncSubmit())

    await act(async () => {
      await result.current.execute(apiCall)
    })
    expect(result.current.error).toBe('fail')

    act(() => { result.current.reset() })

    expect(result.current.loading).toBe(false)
    expect(result.current.phase).toBe(null)
    expect(result.current.progress).toBe(0)
    expect(result.current.error).toBe('')
  })

  it('sets progress to 100 on success', async () => {
    const apiCall = vi.fn().mockResolvedValue({})
    const { result } = renderHook(() => useAsyncSubmit())

    await act(async () => {
      await result.current.execute(apiCall)
    })

    expect(result.current.progress).toBe(100)
  })
})
