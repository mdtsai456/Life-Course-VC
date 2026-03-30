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
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <p className="error-message">
            Something went wrong.{' '}
            <button
              onClick={() => window.location.reload()}
              className="link-button"
            >
              Refresh the page
            </button>
          </p>
        </div>
      )
    }
    return this.props.children
  }
}
