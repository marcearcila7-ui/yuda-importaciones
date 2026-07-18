import { useCallback, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowRight } from 'lucide-react'
import { getPanelVentas } from '../../api/admin'
import type { PanelVentas as PanelVentasT } from '../../types/ventas'
import RangoFechas from './RangoFechas'
import type { Rango } from './RangoFechas'
import TarjetasVentas from './TarjetasVentas'

// Resumen de ventas que se muestra arriba del Dashboard (solo Marcela/admin).
function PanelVentas() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [data, setData] = useState<PanelVentasT | null>(null)
  const [cargando, setCargando] = useState(true)

  const cargar = useCallback((r: Rango) => {
    setCargando(true)
    getPanelVentas(r)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setCargando(false))
  }, [])

  return (
    <section className="flex flex-col gap-4 rounded-2xl border p-4 sm:p-6" style={{ borderColor: 'var(--yuda-border)' }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 style={{ fontWeight: 700, fontSize: 20, color: 'var(--yuda-accent)' }}>💰 {t('ventas.tituloResumen')}</h2>
        <button
          type="button"
          onClick={() => navigate('/ventas')}
          className="flex items-center gap-1 text-sm font-semibold"
          style={{ color: 'var(--yuda-primary)' }}
        >
          {t('ventas.verDetalle')} <ArrowRight size={15} />
        </button>
      </div>
      <RangoFechas onChange={cargar} inicial="30" />
      {data ? (
        <TarjetasVentas data={data} />
      ) : (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {cargando ? t('ventas.cargando') : t('ventas.sinDatos')}
        </p>
      )}
    </section>
  )
}

export default PanelVentas
