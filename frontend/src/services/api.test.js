import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { cloneVoice, checkHealth } from './api'

function mockFetchResponse({ ok = true, status = 200, headers = {}, body = null, json = null, blob = null }) {
  const hmap = new Map(Object.entries(headers))
  return {
    ok,
    status,
    headers: { get: (k) => hmap.get(k) ?? hmap.get(k.toLowerCase()) ?? null },
    json: async () => (json !== null ? json : JSON.parse(body ?? '{}')),
    blob: async () => (blob !== null ? blob : new Blob([body ?? ''])),
  }
}

describe('cloneVoice', () => {
  let originalFetch

  beforeEach(() => {
    originalFetch = globalThis.fetch
    globalThis.fetch = vi.fn()
    let n = 0
    vi.spyOn(URL, 'createObjectURL').mockImplementation(() => `blob:url-${++n}`)
  })
  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns url + jobId on success', async () => {
    const blob = new Blob(['payload'])
    globalThis.fetch.mockResolvedValue(mockFetchResponse({
      headers: { 'X-Job-Id': 'job-abc' },
      blob,
    }))
    const result = await cloneVoice(new File(['x'], 'r.webm'), 'hello')
    expect(result.jobId).toBe('job-abc')
    expect(result.url).toMatch(/^blob:url-/)
    expect(result.blob).toBe(blob)
  })

  it('throws with string detail from 4xx response and attaches jobId', async () => {
    globalThis.fetch.mockResolvedValue(mockFetchResponse({
      ok: false, status: 400,
      headers: { 'X-Job-Id': 'job-bad' },
      json: { detail: '文字不得為空。' },
    }))
    await expect(cloneVoice(new File(['x'], 'r'), '')).rejects.toMatchObject({
      message: '文字不得為空。',
      jobId: 'job-bad',
      status: 400,
    })
  })

  it('aggregates array detail from 422 validation errors', async () => {
    globalThis.fetch.mockResolvedValue(mockFetchResponse({
      ok: false, status: 422,
      json: { detail: [{ msg: 'bad file' }, { msg: 'bad text' }] },
    }))
    await expect(cloneVoice(new File(['x'], 'r'), 't')).rejects.toMatchObject({
      message: 'bad file; bad text',
      status: 422,
    })
  })

  it('throws "伺服器回應為空" when response blob is empty', async () => {
    globalThis.fetch.mockResolvedValue(mockFetchResponse({
      headers: { 'X-Job-Id': 'empty-job' },
      blob: new Blob([]),
    }))
    await expect(cloneVoice(new File(['x'], 'r'), 't')).rejects.toMatchObject({
      message: '伺服器回應為空。',
      jobId: 'empty-job',
    })
  })

  it('throws network error message on fetch failure', async () => {
    globalThis.fetch.mockRejectedValue(new TypeError('Failed to fetch'))
    await expect(cloneVoice(new File(['x'], 'r'), 't')).rejects.toMatchObject({
      code: 'NETWORK_ERROR',
      message: '無法連線到伺服器，請檢查網路連線後重試。',
    })
  })

  it('re-throws AbortError without wrapping', async () => {
    const abortErr = new DOMException('aborted', 'AbortError')
    globalThis.fetch.mockRejectedValue(abortErr)
    await expect(cloneVoice(new File(['x'], 'r'), 't')).rejects.toBe(abortErr)
  })

  it('appends language to FormData when provided', async () => {
    const blob = new Blob(['x'])
    globalThis.fetch.mockResolvedValue(mockFetchResponse({ blob }))
    await cloneVoice(new File(['x'], 'r'), 'hi', undefined, { language: 'ja' })
    const [, init] = globalThis.fetch.mock.calls[0]
    const fd = init.body
    expect(fd.get('language')).toBe('ja')
    expect(fd.get('text')).toBe('hi')
  })
})

describe('checkHealth', () => {
  let originalFetch

  beforeEach(() => {
    originalFetch = globalThis.fetch
    globalThis.fetch = vi.fn()
  })
  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  it('returns true when response ok', async () => {
    globalThis.fetch.mockResolvedValue(mockFetchResponse({ ok: true }))
    expect(await checkHealth()).toBe(true)
  })

  it('returns false when response not ok', async () => {
    globalThis.fetch.mockResolvedValue(mockFetchResponse({ ok: false, status: 503 }))
    expect(await checkHealth()).toBe(false)
  })
})
