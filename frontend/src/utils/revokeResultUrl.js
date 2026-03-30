/**
 * Cleanup callback for useAsyncSubmit's onAbortCleanup option.
 * Revokes the object URL from a result object if present.
 *
 * @param {{ url?: string } | null | undefined} result
 */
export function revokeResultUrl(result) {
  if (result?.url) URL.revokeObjectURL(result.url)
}
