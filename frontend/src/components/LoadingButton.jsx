export default function LoadingButton({
  type = 'button',
  loading,
  loadingText,
  children,
  spinnerStyle,
  disabled,
  ...rest
}) {
  return (
    <button {...rest} type={type} disabled={disabled || loading} aria-busy={loading}>
      {loading ? (
        <span className="spinner-wrapper">
          <span className="spinner" style={spinnerStyle} />
          {loadingText}
        </span>
      ) : (
        children
      )}
    </button>
  )
}
