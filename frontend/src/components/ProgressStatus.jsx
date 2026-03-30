export default function ProgressStatus({ phase, labels }) {
  if (!phase || !labels) return null

  const widthMap = { uploading: '45%', processing: '90%', done: '100%' }
  const transitionMap = {
    uploading: 'width 1s ease-out',
    processing: 'width 4s ease-in-out',
    done: 'width 0.3s',
  }

  const label =
    phase === 'uploading' ? labels.uploading
    : phase === 'processing' ? labels.processing
    : null

  return (
    <div className="progress-status">
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{
            width: widthMap[phase] ?? '0%',
            transition: transitionMap[phase] ?? 'none',
          }}
        />
      </div>
      {label && <p className="progress-label">{label}</p>}
    </div>
  )
}
