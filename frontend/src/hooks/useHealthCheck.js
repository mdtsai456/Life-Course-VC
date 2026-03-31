import { useEffect, useState } from 'react'
import { checkHealth } from '../services/api'

const POLL_INTERVAL_MS = 3000

export default function useHealthCheck() {
  const [serviceReady, setServiceReady] = useState(false)

  useEffect(() => {
    let timerId = null
    let cancelled = false

    async function poll() {
      try {
        const ok = await checkHealth()
        if (cancelled) return
        if (ok) {
          setServiceReady(true)
          return // stop polling
        }
      } catch {
        // network error — keep polling
      }
      if (!cancelled) {
        timerId = setTimeout(poll, POLL_INTERVAL_MS)
      }
    }

    poll()

    return () => {
      cancelled = true
      clearTimeout(timerId)
    }
  }, [])

  return serviceReady
}
