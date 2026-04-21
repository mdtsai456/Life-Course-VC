import { useCallback, useEffect, useState } from 'react'
import { checkHealth } from '../services/api'

const POLL_INTERVAL_MS = 3000
const PERIODIC_RECHECK_MS = 5 * 60 * 1000

export default function useHealthCheck() {
  const [serviceReady, setServiceReady] = useState(false)
  const [pollToken, setPollToken] = useState(0)

  const retrigger = useCallback(() => {
    setServiceReady(false)
    setPollToken(n => n + 1)
  }, [])

  useEffect(() => {
    let cancelled = false
    let pollTimer = null
    let periodicTimer = null

    async function poll() {
      try {
        const ok = await checkHealth()
        if (cancelled) return
        if (ok) {
          setServiceReady(true)
          periodicTimer = setTimeout(() => {
            if (cancelled) return
            setServiceReady(false)
            setPollToken(n => n + 1)
          }, PERIODIC_RECHECK_MS)
          return
        }
      } catch {
        // network error — keep polling
      }
      if (!cancelled) {
        pollTimer = setTimeout(poll, POLL_INTERVAL_MS)
      }
    }

    poll()

    return () => {
      cancelled = true
      clearTimeout(pollTimer)
      clearTimeout(periodicTimer)
    }
  }, [pollToken])

  return { serviceReady, retrigger }
}
