import React from "react";

interface Props {
  children: React.ReactNode;
  /** Use false when nested inside a page's own chrome (header/sidebar stay outside). */
  fullPage?: boolean;
  /** Changing this (e.g. an active session id) clears a tripped boundary so switching
   * away from the content that crashed doesn't leave the fallback stuck forever. */
  resetKey?: string | number;
}

interface State {
  hasError: boolean;
}

// Without this, any uncaught render error (e.g. malformed chat history data)
// unmounts the entire React tree, leaving a blank page with no way to recover.
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown, info: unknown) {
    console.error("Unhandled render error caught by ErrorBoundary:", error, info);
  }

  componentDidUpdate(prevProps: Props) {
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: this.props.fullPage === false ? "100%" : "100vh", gap: "1rem", textAlign: "center", padding: "1.5rem" }}>
          <h2>Something went wrong</h2>
          <p>This page ran into an error. Try reloading.</p>
          <button onClick={() => window.location.reload()}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}
