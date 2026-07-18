import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'

export interface Rango {
  desde?: string
  hasta?: string
}

const PRESETS = ['hoy', '7', '30', 'todo', 'custom'] as const
export type Preset = (typeof PRESETS)[number]

// "Hoy" en hora Bogotá como yyyy-mm-dd, para que los rangos coincidan con el backend.
const hoyBogota = (): string =>
  new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' })

const restarDias = (n: number): string => {
  const base = new Date(hoyBogota() + 'T12:00:00')
  base.setDate(base.getDate() - n)
  return base.toLocaleDateString('en-CA')
}

function rangoDePreset(p: Preset, desde: string, hasta: string): Rango {
  const hoy = hoyBogota()
  if (p === 'hoy') return { desde: hoy, hasta: hoy }
  if (p === '7') return { desde: restarDias(6), hasta: hoy }
  if (p === '30') return { desde: restarDias(29), hasta: hoy }
  if (p === 'todo') return {}
  return { desde: desde || undefined, hasta: hasta || undefined }
}

const inputClase =
  'rounded-lg border border-gray-200 px-2 py-1.5 focus:border-[#4B52E8] focus:outline-none'

function RangoFechas({
  onChange,
  inicial = '30',
}: {
  onChange: (r: Rango) => void
  inicial?: Preset
}) {
  const { t } = useTranslation()
  const [preset, setPreset] = useState<Preset>(inicial)
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  // Guardamos onChange en un ref para no re-disparar el efecto cuando el padre
  // redefine la función en cada render.
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange

  useEffect(() => {
    onChangeRef.current(rangoDePreset(preset, desde, hasta))
  }, [preset, desde, hasta])

  const chip = (activo: boolean): CSSProperties =>
    activo
      ? { borderColor: '#4B52E8', backgroundColor: '#EEF0FD', color: '#4B52E8' }
      : { borderColor: '#E5E7EB', color: '#6B7280' }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {PRESETS.map((p) => (
        <button
          key={p}
          type="button"
          onClick={() => setPreset(p)}
          className="rounded-lg border px-3 py-1.5 text-sm font-medium"
          style={chip(preset === p)}
        >
          {t(`ventas.rango.${p}`)}
        </button>
      ))}
      {preset === 'custom' && (
        <div className="flex items-center gap-2 text-sm" style={{ color: '#6B7280' }}>
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className={inputClase}
            style={{ fontSize: 14 }}
          />
          <span>—</span>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className={inputClase}
            style={{ fontSize: 14 }}
          />
        </div>
      )}
    </div>
  )
}

export default RangoFechas
