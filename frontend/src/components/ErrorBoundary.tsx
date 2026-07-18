import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  hasError: boolean
}

// Evita la pantalla en blanco: si algún componente lanza un error de render,
// muestra un mensaje claro con un botón para recargar, en vez de romper toda la app.
class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Queda en la consola para diagnóstico; no se muestra al usuario.
    console.error('ErrorBoundary capturó un error:', error, info)
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          padding: 24,
          textAlign: 'center',
          backgroundColor: '#F9F9F7',
          color: 'var(--yuda-accent)',
        }}
      >
        <div style={{ fontSize: 40 }}>😕</div>
        <h1 style={{ fontWeight: 700, fontSize: 22 }}>Algo salió mal</h1>
        <p style={{ color: 'var(--yuda-text-secondary)', maxWidth: 360 }}>
          Ocurrió un error inesperado. Recargá la página; si el problema sigue, avisá al equipo.
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          style={{
            minHeight: 48,
            padding: '0 24px',
            backgroundColor: 'var(--yuda-primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Recargar
        </button>
      </div>
    )
  }
}

export default ErrorBoundary
