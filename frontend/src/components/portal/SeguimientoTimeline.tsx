import { useTranslation } from 'react-i18next'
import { ExternalLink, Ship } from 'lucide-react'
import { ESTADOS_ENVIO } from '../../types/seguimiento'
import type { Seguimiento } from '../../types/seguimiento'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

function SeguimientoTimeline({ seguimiento }: { seguimiento: Seguimiento }) {
  const { t, i18n } = useTranslation()
  const locale = LOCALES[i18n.language] || 'es-ES'

  const fmtFecha = (s?: string | null) => {
    if (!s) return null
    const [y, m, d] = s.split('-').map(Number)
    if (!y || !m || !d) return s
    return new Date(y, m - 1, d).toLocaleDateString(locale, {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
  }

  const indiceActual = ESTADOS_ENVIO.indexOf(seguimiento.estado as (typeof ESTADOS_ENVIO)[number])
  const hitos = seguimiento.hitos ?? {}
  const tieneEnvio = seguimiento.numero_tracking || seguimiento.naviera || seguimiento.url_tracking

  return (
    <div className="flex flex-col gap-5">
      {/* Novedades destacadas */}
      {seguimiento.novedades && (
        <div className="rounded-xl p-4" style={{ backgroundColor: '#FEF3C7' }}>
          <p className="mb-1 text-sm font-semibold" style={{ color: '#B45309' }}>
            {t('seguimiento.novedades')}
          </p>
          <p className="text-sm" style={{ color: '#92400E', whiteSpace: 'pre-line' }}>
            {seguimiento.novedades}
          </p>
        </div>
      )}

      {/* Datos del envío */}
      {tieneEnvio && (
        <div className="rounded-xl p-4" style={{ backgroundColor: '#EEF0FD' }}>
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold" style={{ color: '#4B52E8' }}>
            <Ship size={16} /> {t('seguimiento.datosEnvio')}
          </p>
          <div className="grid gap-1 text-sm" style={{ color: '#374151' }}>
            {seguimiento.naviera && (
              <p>
                <strong>{t('seguimiento.naviera')}:</strong> {seguimiento.naviera}
              </p>
            )}
            {seguimiento.numero_tracking && (
              <p>
                <strong>{t('seguimiento.numeroTracking')}:</strong>{' '}
                <span style={{ fontFamily: 'monospace' }}>{seguimiento.numero_tracking}</span>
              </p>
            )}
            {seguimiento.fecha_eta && (
              <p>
                <strong>{t('seguimiento.eta')}:</strong> {fmtFecha(seguimiento.fecha_eta)}
              </p>
            )}
          </div>
          {seguimiento.url_tracking && (
            <a
              href={seguimiento.url_tracking}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white"
              style={{ backgroundColor: '#4B52E8' }}
            >
              <ExternalLink size={16} /> {t('seguimiento.consultarTracking')}
            </a>
          )}
        </div>
      )}

      {/* Línea de tiempo */}
      <div>
        <p className="mb-3 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
          {t('seguimiento.estadoEnvio')}
        </p>
        <div className="flex flex-col">
          {ESTADOS_ENVIO.map((k, i) => {
            const alcanzado = i <= indiceActual
            const actual = i === indiceActual
            const hito = hitos[k]
            const esUltimo = i === ESTADOS_ENVIO.length - 1
            return (
              <div key={k} className="flex gap-3">
                {/* Punto + línea */}
                <div className="flex flex-col items-center">
                  <span
                    className="flex items-center justify-center rounded-full"
                    style={{
                      width: 18,
                      height: 18,
                      backgroundColor: alcanzado ? '#4B52E8' : '#E5E7EB',
                      border: actual ? '3px solid #C7CBF7' : 'none',
                    }}
                  />
                  {!esUltimo && (
                    <span
                      style={{
                        width: 2,
                        flex: 1,
                        minHeight: 28,
                        backgroundColor: i < indiceActual ? '#4B52E8' : '#E5E7EB',
                      }}
                    />
                  )}
                </div>
                {/* Texto */}
                <div className="pb-4">
                  <p
                    className="text-sm"
                    style={{ fontWeight: actual ? 700 : 500, color: alcanzado ? '#0D0D0D' : '#9CA3AF' }}
                  >
                    {t(`seguimiento.estados.${k}`)}
                  </p>
                  {hito?.fecha && (
                    <p className="text-xs" style={{ color: '#6B7280' }}>
                      {fmtFecha(hito.fecha)}
                    </p>
                  )}
                  {hito?.nota && (
                    <p className="text-xs" style={{ color: '#6B7280' }}>
                      {hito.nota}
                    </p>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default SeguimientoTimeline
