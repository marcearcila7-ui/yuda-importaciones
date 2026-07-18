import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight, FileText, PackageSearch, RefreshCw } from 'lucide-react'
import PortalLayout from '../../components/portal/PortalLayout'
import { getMisCotizaciones } from '../../api/portal'
import { usePortalStore } from '../../store/portalStore'
import type { CotizacionResumen } from '../../types/portal'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

function PortalCotizaciones() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { cliente } = usePortalStore()
  const [cotizaciones, setCotizaciones] = useState<CotizacionResumen[] | null>(null)
  const [error, setError] = useState(false)

  const cargar = useCallback(() => {
    setError(false)
    setCotizaciones(null)
    getMisCotizaciones()
      .then(setCotizaciones)
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    cargar()
  }, [cargar])

  const fmtFecha = (s: string) => {
    const [y, m, d] = s.split('-').map(Number)
    if (!y || !m || !d) return s
    return new Date(y, m - 1, d).toLocaleDateString(LOCALES[i18n.language] || 'es-ES', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  }

  const chipEstado = (estado: string) =>
    estado === 'entregado'
      ? { backgroundColor: '#D1FAE5', color: '#10B981' }
      : { backgroundColor: '#EEF0FD', color: '#4B52E8' }

  return (
    <PortalLayout>
      <h1 style={{ fontWeight: 700, fontSize: 26, color: '#0D0D0D' }}>
        {t('portal.saludo', { nombre: cliente?.nombre ?? '' })}
      </h1>
      <p className="mb-6 text-sm" style={{ color: '#6B7280' }}>
        {t('portal.subtitulo')}
      </p>

      {error ? (
        <div className="card flex flex-col items-start gap-3">
          <p className="text-sm" style={{ color: '#374151' }}>{t('portal.errorCarga')}</p>
          <button
            type="button"
            onClick={cargar}
            className="flex items-center gap-2 rounded-lg px-4 font-semibold text-white"
            style={{ minHeight: 44, backgroundColor: '#4B52E8', fontSize: 15 }}
          >
            <RefreshCw size={16} /> {t('portal.reintentar')}
          </button>
        </div>
      ) : cotizaciones === null ? (
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {t('portal.cargando')}
        </p>
      ) : cotizaciones.length === 0 ? (
        <div className="card flex flex-col items-center gap-2 py-10 text-center">
          <PackageSearch size={40} style={{ color: '#6B7280' }} />
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {t('portal.sinCotizaciones')}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {cotizaciones.map((c) => (
            <button
              key={c.sesion_id}
              type="button"
              onClick={() => navigate(`/portal/cotizacion/${c.sesion_id}`)}
              className="card flex items-center justify-between gap-3 text-left transition-shadow hover:shadow-md"
            >
              <div className="flex items-center gap-3">
                <span
                  className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl"
                  style={{ backgroundColor: '#EEF0FD', color: '#4B52E8' }}
                >
                  <FileText size={22} />
                </span>
                <div className="min-w-0">
                  <p className="font-semibold" style={{ color: '#0D0D0D' }}>
                    {c.numero}
                  </p>
                  <p className="text-sm" style={{ color: '#6B7280' }}>
                    {fmtFecha(c.fecha)} · {t('portal.productos', { n: c.total_items })} · US$ {c.total_usd.toLocaleString('es-ES')}
                  </p>
                </div>
              </div>
              <div className="flex flex-shrink-0 items-center gap-2">
                <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chipEstado(c.estado)}>
                  {t(`seguimiento.estados.${c.estado}`)}
                </span>
                <ChevronRight size={18} style={{ color: '#6B7280' }} />
              </div>
            </button>
          ))}
        </div>
      )}
    </PortalLayout>
  )
}

export default PortalCotizaciones
