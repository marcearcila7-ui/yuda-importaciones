import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, Box, CheckCircle2, PackageCheck, Send } from 'lucide-react'
import { getCubicaje, responderCubicaje } from '../api/cubicaje'
import type { CubicajeDetalle, CubicajeMensaje } from '../types/cubicaje'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

const COLOR_RESULTADO: Record<string, { bg: string; fg: string }> = {
  sobra: { bg: 'var(--yuda-warning-soft)', fg: 'var(--yuda-warning-dark)' },
  falta: { bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)' },
  ajustado: { bg: 'var(--yuda-success-soft)', fg: 'var(--yuda-success-dark)' },
}

// Pestaña "Cubicaje": el control de cuánto cubicaje calculó bodega para este
// pedido frente al rango de un contenedor (68-72 m3), y la conversación
// alrededor (reportes de bodega, notas, respuestas de la vendedora). Con
// polling rápido para que un reporte nuevo llegue casi al instante.
function CubicajePanel({ sesionId }: { sesionId: string }) {
  const { t, i18n } = useTranslation()
  const [detalle, setDetalle] = useState<CubicajeDetalle | null>(null)
  const [respuesta, setRespuesta] = useState('')
  const [enviando, setEnviando] = useState(false)

  const cargar = useCallback(() => {
    getCubicaje(sesionId).then(setDetalle).catch(() => {})
  }, [sesionId])

  useEffect(() => {
    cargar()
    const id = setInterval(cargar, 8000)
    const onVisible = () => {
      if (document.visibilityState === 'visible') cargar()
    }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [cargar])

  const enviarRespuesta = async () => {
    const texto = respuesta.trim()
    if (!texto) return
    setEnviando(true)
    try {
      await responderCubicaje(sesionId, texto)
      setRespuesta('')
      cargar()
      toast.success(t('cubicaje.respuestaEnviada'))
    } catch {
      toast.error(t('cubicaje.errorResponder'))
    } finally {
      setEnviando(false)
    }
  }

  const locale = LOCALES[i18n.language] || 'es-ES'
  const fmtFecha = (iso: string) =>
    new Date(iso).toLocaleString(locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

  const detalleMensaje = (m: CubicajeMensaje): string | null => {
    if (m.tipo !== 'reporte') return null
    const cbmTexto =
      m.cbm_ajustado != null
        ? t('cubicaje.cbmAjustadoDetalle', { ajustado: m.cbm_ajustado, calculado: m.cbm_calculado })
        : null
    if (m.resultado === 'sobra' && m.referencia && m.cajas_afectadas) {
      return t('cubicaje.detalleSobra', { n: m.cajas_afectadas, referencia: m.referencia })
    }
    if (m.resultado === 'falta' && m.espacio_restante_cbm != null) {
      return cbmTexto
        ? `${t('cubicaje.detalleFalta', { espacio: m.espacio_restante_cbm })} · ${cbmTexto}`
        : t('cubicaje.detalleFalta', { espacio: m.espacio_restante_cbm })
    }
    return cbmTexto ?? t('cubicaje.detalleAjustado')
  }

  if (!detalle) {
    return (
      <div className="card">
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('common.cargando')}</p>
      </div>
    )
  }

  const colores = COLOR_RESULTADO[detalle.resumen.resultado] ?? COLOR_RESULTADO.ajustado

  return (
    <div className="flex flex-col gap-4">
      <div className="card">
        <h2 className="mb-1 flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
          <Box size={18} /> {t('cubicaje.titulo')}
        </h2>
        <p className="mb-3 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('cubicaje.ayuda')}
        </p>
        <div className="flex flex-wrap items-center gap-3 rounded-lg p-3" style={{ backgroundColor: colores.bg }}>
          <PackageCheck size={20} color={colores.fg} />
          <div>
            <p className="text-sm font-semibold" style={{ color: colores.fg }}>
              {t(`cubicaje.resultado.${detalle.resumen.resultado}`)}
            </p>
            <p className="text-xs" style={{ color: colores.fg }}>
              {t('cubicaje.cbmActual', {
                cbm: detalle.resumen.cbm_calculado,
                min: detalle.resumen.limite_min,
                max: detalle.resumen.limite_max,
              })}
            </p>
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-3" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
          {t('cubicaje.hiloTitulo')}
        </h2>
        {detalle.mensajes.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cubicaje.sinMensajes')}</p>
        ) : (
          <div className="flex flex-col gap-3">
            {detalle.mensajes.map((m) => {
              const info = detalleMensaje(m)
              const esRespuesta = m.tipo === 'respuesta'
              return (
                <div
                  key={m.id}
                  className="rounded-lg border p-3 text-sm"
                  style={{
                    borderColor: 'var(--yuda-border)',
                    backgroundColor: esRespuesta ? 'var(--yuda-primary-soft)' : 'var(--yuda-bg)',
                  }}
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <span className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                      {m.autor_nombre || '—'}
                      {m.tipo === 'reporte' && (
                        <span className="ml-2 text-xs font-normal" style={{ color: 'var(--yuda-text-secondary)' }}>
                          {t('cubicaje.tipoReporte')}
                        </span>
                      )}
                    </span>
                    <span className="flex-shrink-0 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {fmtFecha(m.created_at)}
                    </span>
                  </div>
                  {info && (
                    <p className="mb-1 flex items-center gap-1 font-medium" style={{ color: 'var(--yuda-text)' }}>
                      {m.resultado === 'ajustado' ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />} {info}
                    </p>
                  )}
                  {m.mensaje && <p style={{ color: 'var(--yuda-text)' }}>{m.mensaje}</p>}
                </div>
              )
            })}
          </div>
        )}

        <label className="mt-4 flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('cubicaje.responderLabel')}
          <textarea
            value={respuesta}
            onChange={(e) => setRespuesta(e.target.value)}
            rows={2}
            placeholder={t('cubicaje.responderPlaceholder')}
            className="rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none"
            style={{ fontSize: 15 }}
          />
        </label>
        <button
          type="button"
          onClick={enviarRespuesta}
          disabled={enviando || !respuesta.trim()}
          className="mt-2 flex min-h-[44px] items-center justify-center gap-2 self-start rounded-lg px-4 font-semibold text-white disabled:opacity-60"
          style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 15 }}
        >
          <Send size={16} /> {enviando ? t('common.subiendo') : t('cubicaje.responderBoton')}
        </button>
      </div>
    </div>
  )
}

export default CubicajePanel
