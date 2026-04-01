import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('Uncaught error:', error, info)
    if (typeof this.props.onError === 'function') {
      this.props.onError(error, info)
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <p className="error-message">
            發生錯誤。{' '}
            <button
              onClick={() => window.location.reload()}
              className="link-button"
            >
              重新整理頁面
            </button>
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
