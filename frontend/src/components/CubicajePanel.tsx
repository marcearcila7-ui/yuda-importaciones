import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, Box, CheckCircle2, FileText, Paperclip, PackageCheck, Send, X } from 'lucide-react'
import { getCubicaje, responderCubicaje, subirAdjuntoCubicaje } from '../api/cubicaje'
import type { CubicajeAdjunto, CubicajeDetalle, CubicajeMensaje } from '../types/cubicaje'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

const COLOR_RESULTADO: Record<string, { bg: string; fg: string }> = {
  sobra: { bg: 'var(--yuda-warning-soft)', fg: 'var(--yuda-warning-dark)' },
  falta: { bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)' },
  ajustado: { bg: 'var(--yuda-success-soft)', fg: 'var(--yuda-success-dark)' },
}

// Una foto se ve directo, un video con su reproductor, y cualquier otro
// archivo (PDF, Excel, CSV) como un link con ícono -bodega y la vendedora
// necesitan poder mandarse las tres cosas, no solo texto.
function AdjuntoMensaje({ adjunto, claro }: { adjunto: CubicajeAdjunto; claro: boolean }) {
  if (adjunto.tipo === 'imagen') {
    return (
      <a href={adjunto.url} target="_blank" rel="noreferrer" className="mt-1 block">
        <img src={adjunto.url} alt={adjunto.nombre || ''} className="max-h-48 rounded-lg object-cover" />
      </a>
    )
  }
  if (adjunto.tipo === 'video') {
    return (
      <video src={adjunto.url} controls className="mt-1 max-h-48 rounded-lg" style={{ maxWidth: '100%' }} />
    )
  }
  return (
    <a
      href={adjunto.url}
      target="_blank"
      rel="noreferrer"
      className="mt-1 flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium underline"
      style={{ backgroundColor: claro ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.05)' }}
    >
      <FileText size={14} /> {adjunto.nombre || adjunto.url}
    </a>
  )
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
  const [adjuntosPendientes, setAdjuntosPendientes] = useState<CubicajeAdjunto[]>([])
  const [subiendoAdjunto, setSubiendoAdjunto] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    if (!texto && adjuntosPendientes.length === 0) return
    setEnviando(true)
    try {
      await responderCubicaje(sesionId, texto, adjuntosPendientes.length ? adjuntosPendientes : undefined)
      setRespuesta('')
      setAdjuntosPendientes([])
      cargar()
      toast.success(t('cubicaje.respuestaEnviada'))
    } catch {
      toast.error(t('cubicaje.errorResponder'))
    } finally {
      setEnviando(false)
    }
  }

  // Sube el archivo de una vez al elegirlo (no espera a "enviar"): así se ve
  // como una miniatura lista antes de mandar el mensaje, igual que en
  // cualquier chat.
  const elegirAdjunto = async (archivo: File | undefined) => {
    if (!archivo) return
    setSubiendoAdjunto(true)
    try {
      const adjunto = await subirAdjuntoCubicaje(sesionId, archivo)
      setAdjuntosPendientes((a) => [...a, adjunto])
    } catch {
      toast.error(t('cubicaje.errorAdjunto'))
    } finally {
      setSubiendoAdjunto(false)
    }
  }

  const quitarAdjuntoPendiente = (url: string) => {
    setAdjuntosPendientes((a) => a.filter((x) => x.url !== url))
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
        <h2 className="mb-1" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
          {t('cubicaje.hiloTitulo')}
        </h2>
        {/* Con quién es la conversación: antes no se sabía si el pedido ya
            tenía a alguien de bodega trabajándolo o seguía sin asignar. */}
        <p className="mb-3 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
          {detalle.bodega_asignado_a_nombre
            ? t('cubicaje.chatCon', { nombre: detalle.bodega_asignado_a_nombre })
            : t('cubicaje.chatSinAsignar')}
        </p>
        {/* El hilo como una conversación real: los mensajes de la vendedora
            (este lado) van a la derecha, los de bodega a la izquierda -como
            cualquier chat, no una lista de tarjetas iguales. */}
        {detalle.mensajes.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cubicaje.sinMensajes')}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {detalle.mensajes.map((m) => {
              const info = detalleMensaje(m)
              const esRespuesta = m.tipo === 'respuesta'
              return (
                <div key={m.id} className={`flex ${esRespuesta ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className="max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm sm:max-w-[70%]"
                    style={{
                      backgroundColor: esRespuesta ? 'var(--yuda-primary)' : '#F3F4F6',
                      color: esRespuesta ? 'white' : 'var(--yuda-text)',
                      borderBottomRightRadius: esRespuesta ? 4 : undefined,
                      borderBottomLeftRadius: esRespuesta ? undefined : 4,
                    }}
                  >
                    <p className="text-xs font-semibold" style={{ opacity: 0.8 }}>
                      {m.autor_nombre || '—'}
                    </p>
                    {info && (
                      <p className="mt-0.5 flex items-center gap-1 font-medium">
                        {m.resultado === 'ajustado' ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />} {info}
                      </p>
                    )}
                    {m.mensaje && <p className="mt-0.5">{m.mensaje}</p>}
                    {m.adjuntos?.map((a, i) => (
                      <AdjuntoMensaje key={`${a.url}-${i}`} adjunto={a} claro={esRespuesta} />
                    ))}
                    <p className="mt-1 text-right text-xs" style={{ opacity: 0.7 }}>
                      {fmtFecha(m.created_at)}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {adjuntosPendientes.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {adjuntosPendientes.map((a) => (
              <div key={a.url} className="relative">
                {a.tipo === 'imagen' ? (
                  <img src={a.url} alt="" style={{ width: 56, height: 56 }} className="rounded-lg object-cover" />
                ) : (
                  <div
                    className="flex items-center gap-1 rounded-lg px-2 text-xs font-medium"
                    style={{ height: 56, backgroundColor: '#F3F4F6', color: 'var(--yuda-text)' }}
                  >
                    <FileText size={14} /> {a.nombre || a.tipo}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => quitarAdjuntoPendiente(a.url)}
                  aria-label={t('common.quitar')}
                  className="absolute -right-1.5 -top-1.5 flex items-center justify-center rounded-full text-white"
                  style={{ width: 18, height: 18, backgroundColor: 'var(--yuda-error)' }}
                >
                  <X size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="mt-3 flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/webm,application/pdf,.csv,.xls,.xlsx"
            className="hidden"
            disabled={subiendoAdjunto}
            onChange={(e) => {
              const f = e.target.files?.[0]
              e.target.value = ''
              elegirAdjunto(f)
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={subiendoAdjunto}
            aria-label={t('cubicaje.adjuntarBoton')}
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full disabled:opacity-60"
            style={{ backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }}
          >
            <Paperclip size={18} />
          </button>
          <textarea
            value={respuesta}
            onChange={(e) => setRespuesta(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                enviarRespuesta()
              }
            }}
            rows={1}
            placeholder={t('cubicaje.responderPlaceholder')}
            className="flex-1 resize-none rounded-full border border-gray-200 px-4 py-2.5 focus:border-[var(--yuda-primary)] focus:outline-none"
            style={{ fontSize: 15 }}
          />
          <button
            type="button"
            onClick={enviarRespuesta}
            disabled={enviando || (!respuesta.trim() && adjuntosPendientes.length === 0)}
            aria-label={t('cubicaje.responderBoton')}
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full text-white disabled:opacity-60"
            style={{ backgroundColor: 'var(--yuda-primary)' }}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}

export default CubicajePanel
