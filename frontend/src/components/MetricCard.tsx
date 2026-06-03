import type { ReactNode } from 'react'

interface MetricCardProps {
  titulo: string
  valor: string | number
  subtitulo?: string
  icono: ReactNode
  color?: string
  tendencia?: 'up' | 'down' | 'neutral'
  porcentaje?: number
}

// Convierte un hex a rgba con la opacidad dada (para el círculo del ícono)
function hexAlpha(hex: string, alpha: number): string {
  const h = hex.replace('#', '')
  const r = parseInt(h.substring(0, 2), 16)
  const g = parseInt(h.substring(2, 4), 16)
  const b = parseInt(h.substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function MetricCard({
  titulo,
  valor,
  subtitulo,
  icono,
  color = '#4B52E8',
  tendencia,
  porcentaje,
}: MetricCardProps) {
  const colorTendencia =
    tendencia === 'up' ? '#10B981' : tendencia === 'down' ? '#EF4444' : '#6B7280'
  const flecha = tendencia === 'up' ? '↑' : tendencia === 'down' ? '↓' : '→'

  return (
    <div className="card flex flex-col gap-3 p-4 sm:p-6">
      <div className="flex items-start justify-between">
        <span
          className="flex h-11 w-11 items-center justify-center rounded-full"
          style={{ backgroundColor: hexAlpha(color, 0.1), color }}
        >
          {icono}
        </span>
        {tendencia && porcentaje !== undefined && (
          <span className="text-xs font-semibold" style={{ color: colorTendencia }}>
            {flecha} {porcentaje}%
          </span>
        )}
      </div>
      <div>
        <p className="text-2xl sm:text-[32px]" style={{ fontWeight: 700, color: '#0D0D0D', lineHeight: 1.1 }}>
          {valor}
        </p>
        <p className="mt-1 text-sm" style={{ color: '#6B7280' }}>
          {titulo}
        </p>
        {subtitulo && <p className="mt-0.5 text-xs text-gray-400">{subtitulo}</p>}
      </div>
    </div>
  )
}

export default MetricCard
