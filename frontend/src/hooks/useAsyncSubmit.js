import { useCallback, useRef, useState } from 'react'

/**
 * Custom hook encapsulating the shared async submit pattern:
 * abort previous → create AbortController → phase timer → try/catch/finally.
 *
 * Note: after abort(), `loading` remains true until `reset()` is called.
 * Components should call `reset()` in cleanup effects and on visibility changes.
 *
 * @returns {{ execute, loading, error, phase, abort, reset, abortControllerRef, phaseTimerRef }}
 */
export default function useAsyncSubmit() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [phase, setPhase] = useState(null)

  const abortControllerRef = useRef(null)
  const phaseTimerRef = useRef(null)
  const uploadTimerRef = useRef(null)

  const abort = useCallback(() => {
    abortControllerRef.current?.abort()
    clearTimeout(phaseTimerRef.current)
    clearTimeout(uploadTimerRef.current)
  }, [])

  const reset = useCallback(() => {
    abort()
    setLoading(false)
    setPhase(null)
    setError('')
  }, [abort])

  /**
   * Execute an async API call with full abort + phase management.
   *
   * @param {(signal: AbortSignal) => Promise<any>} apiCall - The API function to call.
   * @param {object} [options]
   * @param {(result: any) => void} [options.onSuccess] - Called with the result on success.
   * @param {(err: Error) => void} [options.onError] - Called on non-abort errors. Defaults to setError(err.message).
   * @param {(result: any) => void} [options.onAbortCleanup] - Called with the API result when result was obtained but signal was aborted.
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
    setPhase('uploading')

    const localUploadTimer = setTimeout(() => setPhase('processing'), 800)
    uploadTimerRef.current = localUploadTimer

    try {
      const result = await apiCall(localController.signal)
      clearTimeout(localUploadTimer)
      if (localController.signal.aborted) {
        onAbortCleanup?.(result)
        return
      }
      setPhase('done')
      phaseTimerRef.current = setTimeout(() => setPhase(null), 500)
      onSuccess?.(result)
    } catch (err) {
      clearTimeout(localUploadTimer)
      if (err.name === 'AbortError') return
      if (!localController.signal.aborted) {
        setPhase(null)
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

  return { execute, loading, error, setError, phase, abort, reset, abortControllerRef, phaseTimerRef }
}
