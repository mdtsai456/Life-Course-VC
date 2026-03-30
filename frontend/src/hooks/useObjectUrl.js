import { useEffect, useState } from 'react'

/**
 * Create and manage an object URL derived from a Blob/File source.
 * URL is created when source changes; old URL is revoked automatically.
 *
 * @param {Blob|File|null} source
 * @returns {string|null}
 */
export function useDerivedObjectUrl(source) {
  const [url, setUrl] = useState(null)

  useEffect(() => {
    if (!source) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync with external resource lifecycle
      setUrl(null)
      return
    }
    const objectUrl = URL.createObjectURL(source)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [source])

  return url
}

/**
 * Manage an externally-set object URL with automatic revocation on change/unmount.
 * Returns [url, setUrl] like useState, but revokes the previous URL whenever
 * a new one is set and revokes on unmount.
 *
 * @returns {[string|null, (url: string|null) => void]}
 */
export function useManagedObjectUrl() {
  const [url, setUrl] = useState(null)

  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL(url)
    }
  }, [url])

  return [url, setUrl]
}
