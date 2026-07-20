import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ChevronRight, FileText, PackageSearch, RefreshCw, Wallet } from 'lucide-react'
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
      ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
      : { backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }

  return (
    <PortalLayout>
      <h1 style={{ fontWeight: 700, fontSize: 26, color: 'var(--yuda-accent)' }}>
        {t('portal.saludo', { nombre: cliente?.nombre ?? '' })}
      </h1>
      <p className="mb-4 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
        {t('portal.subtitulo')}
      </p>

      <button
        type="button"
        onClick={() => navigate('/portal/cuenta')}
        className="card mb-6 flex w-full items-center justify-between text-left"
        style={{ cursor: 'pointer' }}
      >
        <span className="flex items-center gap-2" style={{ fontWeight: 600, color: 'var(--yuda-accent)' }}>
          <Wallet size={20} /> {t('portal.verCuenta')}
        </span>
        <ChevronRight size={18} style={{ color: 'var(--yuda-primary)' }} />
      </button>

      {error ? (
        <div className="card flex flex-col items-start gap-3">
          <p className="text-sm" style={{ color: 'var(--yuda-text)' }}>{t('portal.errorCarga')}</p>
          <button
            type="button"
            onClick={cargar}
            className="flex items-center gap-2 rounded-lg px-4 font-semibold text-white"
            style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', fontSize: 15 }}
          >
            <RefreshCw size={16} /> {t('portal.reintentar')}
          </button>
        </div>
      ) : cotizaciones === null ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('portal.cargando')}
        </p>
      ) : cotizaciones.length === 0 ? (
        <div className="card flex flex-col items-center gap-2 py-10 text-center">
          <PackageSearch size={40} style={{ color: 'var(--yuda-text-secondary)' }} />
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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
                  style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                >
                  <FileText size={22} />
                </span>
                <div className="min-w-0">
                  <p className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                    {c.numero}
                  </p>
                  <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {fmtFecha(c.fecha)} · {t('portal.productos', { n: c.total_items })} · US$ {c.total_usd.toLocaleString('es-ES')}
                  </p>
                </div>
              </div>
              <div className="flex flex-shrink-0 items-center gap-2">
                <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chipEstado(c.estado)}>
                  {t(`seguimiento.estados.${c.estado}`)}
                </span>
                <ChevronRight size={18} style={{ color: 'var(--yuda-text-secondary)' }} />
              </div>
            </button>
          ))}
        </div>
      )}
    </PortalLayout>
  )
}

export default PortalCotizaciones
