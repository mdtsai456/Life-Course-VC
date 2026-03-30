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
    <button type={type} disabled={disabled || loading} aria-busy={loading} {...rest}>
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
