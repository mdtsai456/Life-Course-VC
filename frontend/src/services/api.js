const NETWORK_ERROR_MESSAGE = '無法連線到伺服器，請檢查網路連線後重試。'

function _makeError(message, { jobId = null, status = null } = {}) {
  const err = new Error(message)
  if (jobId) err.jobId = jobId
  if (status !== null) err.status = status
  return err
}

async function postForBlob(url, formData, fallbackMessage, signal) {
  let response
  try {
    response = await fetch(url, {
      method: 'POST',
      body: formData,
      signal,
    })
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw _makeError(NETWORK_ERROR_MESSAGE)
  }

  const jobId = response.headers.get('X-Job-Id')

  if (!response.ok) {
    let message = fallbackMessage
    try {
      const errorData = await response.json()
      if (typeof errorData.detail === 'string') {
        message = errorData.detail
      } else if (Array.isArray(errorData.detail)) {
        message = errorData.detail.map(e => e.msg ?? e.message ?? String(e)).join('; ')
      }
    } catch (err) {
      if (err.name === 'AbortError') throw err
    }
    throw _makeError(message, { jobId, status: response.status })
  }

  let blob
  try {
    blob = await response.blob()
  } catch (err) {
    if (err.name === 'AbortError') throw err
    throw _makeError(NETWORK_ERROR_MESSAGE, { jobId })
  }
  if (blob.size === 0) {
    throw _makeError('伺服器回應為空。', { jobId })
  }
  return { url: URL.createObjectURL(blob), blob, jobId }
}

export async function cloneVoice(audioFile, text, signal, { language } = {}) {
  const formData = new FormData()
  formData.append('file', audioFile)
  formData.append('text', text ?? '')
  if (language) formData.append('language', language)
  return postForBlob('/api/clone-voice', formData, '語音克隆失敗。', signal)
}

export async function checkHealth() {
  const response = await fetch('/health')
  return response.ok
}
