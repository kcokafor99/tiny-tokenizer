import { Component, type ErrorInfo, type ReactNode } from "react"
import { log } from "@/lib/logger"

type Props = { children: ReactNode }
type State = { error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    log.error("react_error_boundary", {
      message: error.message,
      stack: error.stack ?? "",
      componentStack: info.componentStack ?? "",
    })
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex h-full items-center justify-center p-8">
          <div className="max-w-md rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Something went wrong</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              The error has been logged. Try refreshing the page.
            </p>
            <pre className="mt-4 max-h-40 overflow-auto rounded bg-[var(--color-surface-subtle)] p-2 font-mono text-xs">
              {this.state.error.message}
            </pre>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
