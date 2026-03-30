import { useEffect, useRef, useState } from 'react'
import { cloneVoice } from '../services/api'
import { revokeResultUrl } from '../utils/revokeResultUrl'
import useAsyncSubmit from '../hooks/useAsyncSubmit'
import { useManagedObjectUrl } from '../hooks/useObjectUrl'
import LoadingButton from './LoadingButton'
import ProgressStatus from './ProgressStatus'

// --- Pure helpers (outside component, never recreated) ---

function getSupportedMimeType() {
  if (typeof MediaRecorder === 'undefined') return ''
  const candidates = [
    'audio/mp4;codecs=mp4a.40.2', // Safari 14.1+ (must come first)
    'audio/mp4',
    'audio/webm;codecs=opus',     // Chrome / Edge / Firefox
    'audio/webm',
    'audio/ogg;codecs=opus',      // Firefox fallback
  ]
  return candidates.find(t => MediaRecorder.isTypeSupported(t)) ?? ''
}

function mimeTypeToExtension(mimeType) {
  if (mimeType.startsWith('audio/webm')) return 'webm'
  if (mimeType.startsWith('audio/ogg'))  return 'ogg'
  if (mimeType.startsWith('audio/mp4'))  return 'mp4'
  return 'audio'
}

function formatTime(seconds) {
  const m = String(Math.floor(seconds / 60)).padStart(2, '0')
  const s = String(seconds % 60).padStart(2, '0')
  return `${m}:${s}`
}

function mapGetUserMediaError(err) {
  const name = err.name
  if (name === 'NotAllowedError' || name === 'PermissionDeniedError')
    return '麥克風存取被拒絕。請在瀏覽器網址列點擊鎖頭圖示，允許麥克風存取後重試。'
  if (name === 'NotFoundError' || name === 'DevicesNotFoundError')
    return '找不到麥克風裝置。請連接麥克風後重試。'
  if (name === 'NotReadableError' || name === 'TrackStartError')
    return '麥克風正被其他應用程式使用。請關閉其他使用麥克風的程式後重試。'
  if (name === 'SecurityError')
    return '麥克風存取需要 HTTPS 連線。'
  return `無法存取麥克風：${err.message}`
}

const CLONE_PROGRESS_LABELS = { uploading: '上傳錄音中...', processing: '克隆聲音中...' }

// --- Component ---

export default function VoiceCloner() {
  // UI state
  const [isAcquiringMic, setIsAcquiringMic] = useState(false)
  const [isRecording, setIsRecording]       = useState(false)
  const [audioBlob, setAudioBlob]           = useState(null)
  const [recordingSeconds, setRecordingSeconds] = useState(0)
  const [text, setText]                     = useState('')
  const [resultUrl, setResultUrl]           = useManagedObjectUrl()
  const [recordingMimeType, setRecordingMimeType] = useState('')

  const { execute, loading, error, setError, phase, reset } = useAsyncSubmit()

  // External resource refs (no re-render on change)
  const mediaRecorderRef = useRef(null)
  const streamRef        = useRef(null)
  const chunksRef        = useRef([])
  const timerRef         = useRef(null)
  const disposedRef      = useRef(false)

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disposedRef.current = true
      clearInterval(timerRef.current)
      reset()
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      streamRef.current?.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
  }, [reset])

  function stopMicTracks() {
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
  }

  async function handleStartRecording() {
    // Secure context & capability guard
    if (!window.isSecureContext && location.hostname !== 'localhost') {
      setError('麥克風存取需要 HTTPS 連線。')
      return
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('您的瀏覽器不支援音頻錄製。請使用 Chrome、Firefox 或 Safari 14.1+。')
      return
    }

    setError('')
    setResultUrl(null)
    setAudioBlob(null)
    chunksRef.current = []
    setIsAcquiringMic(true)

    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (err) {
      setError(mapGetUserMediaError(err))
      setIsAcquiringMic(false)
      return
    }

    if (disposedRef.current) {
      stream.getTracks().forEach(t => t.stop())
      return
    }

    streamRef.current = stream
    setIsAcquiringMic(false)

    const mimeType = getSupportedMimeType()
    let recorder
    try {
      recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
    } catch {
      recorder = new MediaRecorder(stream)
    }

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        chunksRef.current.push(e.data)
      }
    }

    recorder.onstop = () => {
      // Defer one microtask so any trailing ondataavailable fires first
      Promise.resolve().then(() => {
        if (disposedRef.current) {
          chunksRef.current = []
          return
        }
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
        chunksRef.current = []
        setAudioBlob(blob)
        setRecordingMimeType(recorder.mimeType)
        stopMicTracks()
      })
    }

    recorder.onerror = () => {
      setError('錄音發生錯誤，請重試。')
      clearInterval(timerRef.current)
      setIsRecording(false)
      stopMicTracks()
    }

    mediaRecorderRef.current = recorder
    recorder.start()

    setIsRecording(true)
    setRecordingSeconds(0)
    timerRef.current = setInterval(() => {
      setRecordingSeconds(s => s + 1)
    }, 1000)
  }

  function handleStopRecording() {
    const recorder = mediaRecorderRef.current
    if (recorder && (recorder.state === 'recording' || recorder.state === 'paused')) {
      recorder.stop()
    }
    clearInterval(timerRef.current)
    setIsRecording(false)
    // stopMicTracks() is called inside recorder.onstop after blob assembly
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!audioBlob || !text.trim()) return

    setResultUrl(null)

    const ext = recordingMimeType ? mimeTypeToExtension(recordingMimeType) : 'audio'
    const audioFile = new File([audioBlob], `recording.${ext}`, { type: audioBlob.type })

    execute(
      (signal) => cloneVoice(audioFile, text.trim(), signal),
      {
        onSuccess: ({ url }) => setResultUrl(url),
        onAbortCleanup: revokeResultUrl,
      },
    )
  }

  const isDisabled = !audioBlob || !text.trim() || loading || isRecording || isAcquiringMic

  return (
    <div className="voice-cloner">
      <p className="voice-cloner-desc">
        錄製您的聲音樣本，輸入文字，即可生成以您的聲音朗讀的音檔。
      </p>

      <form className="clone-form" onSubmit={handleSubmit}>

        {/* Recording section */}
        <div className="record-section">
          {!isRecording ? (
            <LoadingButton
              type="button"
              className="record-button"
              onClick={handleStartRecording}
              disabled={isAcquiringMic || loading}
              loading={isAcquiringMic}
              loadingText="等待麥克風…"
              spinnerStyle={{ borderTopColor: '#fff', borderColor: 'rgba(255,255,255,0.4)' }}
            >
              ● 開始錄音
            </LoadingButton>
          ) : (
            <button
              type="button"
              className="record-button recording"
              onClick={handleStopRecording}
            >
              ■ 停止錄音
            </button>
          )}

          {isRecording && (
            <span className="recording-timer" aria-live="polite">
              {formatTime(recordingSeconds)}
            </span>
          )}

          {audioBlob && !isRecording && (
            <span className="recorded-status">
              ✓ 已錄製 {formatTime(recordingSeconds)}
            </span>
          )}
        </div>

        {/* Text input */}
        <textarea
          aria-label="Text to read aloud"
          className="prompt-input"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="輸入希望以您的聲音朗讀的文字…"
          rows={4}
          disabled={isRecording || loading}
        />

        {/* Submit */}
        <LoadingButton
          type="submit"
          className="submit-button"
          disabled={isDisabled}
          loading={loading}
          loadingText="處理中…"
        >
          送出
        </LoadingButton>
        <ProgressStatus phase={phase} labels={CLONE_PROGRESS_LABELS} />
      </form>

      {error && <p className="error-message">{error}</p>}

      {resultUrl && (
        <div className="audio-result">
          <p className="preview-title">結果音檔</p>
          <audio
            key={resultUrl}
            controls
            src={resultUrl}
            className="audio-player"
          />
          <a
            href={resultUrl}
            download="cloned-voice.wav"
            className="download-button download-audio-btn"
          >
            下載音檔
          </a>
        </div>
      )}
    </div>
  )
}
