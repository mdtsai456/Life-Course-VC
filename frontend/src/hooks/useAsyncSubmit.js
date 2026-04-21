import { useCallback, useRef, useState } from 'react'

/**
 * Custom hook encapsulating the shared async submit pattern:
 * abort previous → create AbortController → phase timer → try/catch/finally.
 *
 * Note: after abort(), `loading` remains true until `reset()` is called.
 * Components should call `reset()` in cleanup effects and on visibility changes.
 *
 * @returns {{ execute, loading, error, phase, progress, abort, reset, abortControllerRef, phaseTimerRef }}
 */
export default function useAsyncSubmit() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [phase, setPhase] = useState(null)
  const [progress, setProgress] = useState(0)

  const abortControllerRef = useRef(null)
  const phaseTimerRef = useRef(null)
  const uploadTimerRef = useRef(null)
  const progressTimerRef = useRef(null)

  const _clearProgressTimer = () => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current)
      progressTimerRef.current = null
    }
  }

  const abort = useCallback(() => {
    abortControllerRef.current?.abort()
    clearTimeout(phaseTimerRef.current)
    clearTimeout(uploadTimerRef.current)
    _clearProgressTimer()
  }, [])

  const reset = useCallback(() => {
    abort()
    setLoading(false)
    setPhase(null)
    setProgress(0)
    setError('')
  }, [abort])

  /**
   * Execute an async API call with full abort + phase management.
   *
   * @param {(signal: AbortSignal) => Promise<any>} apiCall
   * @param {object} [options]
   * @param {(result: any) => void} [options.onSuccess]
   * @param {(err: Error) => void} [options.onError]
   * @param {(result: any) => void} [options.onAbortCleanup]
   */
  const execute = useCallback(async (apiCall, options = {}) => {
    const { onSuccess, onError, onAbortCleanup } = options

    abortControllerRef.current?.abort()
    const localController = new AbortController()
    abortControllerRef.current = localController
    setLoading(true)
    setError('')
    clearTimeout(phaseTimerRef.current)
    clearTimeout(uploadTimerRef.current)
    _clearProgressTimer()
    setPhase('uploading')
    setProgress(0)

    const localUploadTimer = setTimeout(() => setPhase('processing'), 800)
    uploadTimerRef.current = localUploadTimer

    // Fake progress ramp: 0 → 95 over ~30s; stays at 95 until done/error.
    progressTimerRef.current = setInterval(() => {
      if (localController.signal.aborted) return
      setProgress(p => (p < 95 ? p + 1 : p))
    }, 300)

    try {
      const result = await apiCall(localController.signal)
      clearTimeout(localUploadTimer)
      _clearProgressTimer()
      if (localController.signal.aborted) {
        onAbortCleanup?.(result)
        return
      }
      setPhase('done')
      setProgress(100)
      phaseTimerRef.current = setTimeout(() => setPhase(null), 500)
      onSuccess?.(result)
    } catch (err) {
      clearTimeout(localUploadTimer)
      _clearProgressTimer()
      if (err.name === 'AbortError') return
      if (!localController.signal.aborted) {
        setPhase(null)
        setProgress(0)
        if (onError) {
          onError(err)
        } else {
          setError(err.message || '發生錯誤，請重試。')
        }
      }
    } finally {
      if (!localController.signal.aborted) {
        setLoading(false)
      }
    }
  }, [])

  return { execute, loading, error, setError, phase, progress, abort, reset, abortControllerRef, phaseTimerRef }
}
