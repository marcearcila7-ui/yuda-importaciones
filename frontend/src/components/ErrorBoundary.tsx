import { Component } from 'react'
import type { ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  hasError: boolean
  // Se guarda el detalle tecnico para poder mostrarlo: un error que no dice nada
  // obliga a adivinar, y la vendedora no tiene forma de contar que paso.
  detalle: string | null
}

// Evita la pantalla en blanco: si algún componente lanza un error de render,
// muestra un mensaje claro con un botón para recargar, en vez de romper toda la app.
class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, detalle: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, detalle: `${error.name}: ${error.message}` }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
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
          Ocurrió un error inesperado. Recarga la página; si el problema sigue, avisa al equipo
          y cuéntale lo que dice el detalle.
        </p>
        {this.state.detalle && (
          <details style={{ maxWidth: 560, textAlign: 'left' }}>
            <summary style={{ cursor: 'pointer', color: 'var(--yuda-primary)', fontSize: 14 }}>
              Ver detalle técnico
            </summary>
            <pre
              style={{
                marginTop: 8,
                padding: 12,
                borderRadius: 8,
                backgroundColor: '#FEF2F2',
                color: '#92400E',
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {this.state.detalle}
            </pre>
          </details>
        )}
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
