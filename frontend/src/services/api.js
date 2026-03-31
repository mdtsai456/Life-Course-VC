async function postForBlob(url, formData, fallbackMessage, signal) {
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
    signal,
  })

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
    throw new Error(message)
  }

  const blob = await response.blob()
  if (blob.size === 0) {
    throw new Error('伺服器回應為空。')
  }
  return { url: URL.createObjectURL(blob), blob }
}

export async function cloneVoice(audioFile, text, signal) {
  const formData = new FormData()
  formData.append('file', audioFile)
  formData.append('text', text ?? '')
  return postForBlob('/api/clone-voice', formData, '語音克隆失敗。', signal)
}

export async function checkHealth() {
  const response = await fetch('/health')
  return response.ok
}
