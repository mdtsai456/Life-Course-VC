export default function ProgressStatus({ phase, labels, progress }) {
  if (!phase || !labels) return null

  const label =
    phase === 'uploading' ? labels.uploading
    : phase === 'processing' ? labels.processing
    : null
  const clampedProgress = Math.max(0, Math.min(100, Number.isFinite(progress) ? progress : 0))

  return (
    <div className="progress-status">
      <div
        className="progress-bar-track"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clampedProgress}
      >
        <div
          className="progress-bar-fill"
          style={{
            width: `${clampedProgress}%`,
            transition: 'width 0.3s ease',
          }}
        />
      </div>
      {label && <p className="progress-label">{label}</p>}
    </div>
  )
}
