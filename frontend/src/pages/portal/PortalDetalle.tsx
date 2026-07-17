import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ArrowLeft, FileSpreadsheet, FileText, Send } from 'lucide-react'
import PortalLayout from '../../components/portal/PortalLayout'
import SeguimientoTimeline from '../../components/portal/SeguimientoTimeline'
import { descargarCotizacion, enviarPedidoPortal, getCotizacionDetalle } from '../../api/portal'
import type { CotizacionDetalle, PortalItem } from '../../types/portal'

function descripcion(item: PortalItem, idioma: string): string {
  if (idioma === 'en') return item.descripcion_en || item.descripcion_es || ''
  if (idioma === 'zh') return item.descripcion_zh || item.descripcion_es || ''
  return item.descripcion_es || item.descripcion_en || ''
}

function PortalDetalle() {
  const { sesionId } = useParams<{ sesionId: string }>()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [detalle, setDetalle] = useState<CotizacionDetalle | null>(null)
  const [noEncontrada, setNoEncontrada] = useState(false)
  const [descargando, setDescargando] = useState<'excel' | 'pdf' | null>(null)
  // Pedido del cliente: cajas por producto (item_id -> texto) y notas.
  const [cantidades, setCantidades] = useState<Record<string, string>>({})
  const [notas, setNotas] = useState('')
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (!sesionId) return
    getCotizacionDetalle(sesionId)
      .then((d) => {
        setDetalle(d)
        const init: Record<string, string> = {}
        d.items.forEach((it) => {
          if (it.cantidad_solicitada != null) init[it.item_id] = String(it.cantidad_solicitada)
        })
        setCantidades(init)
        setNotas(d.notas_cliente ?? '')
      })
      .catch(() => setNoEncontrada(true))
  }, [sesionId])

  const descargar = async (tipo: 'excel' | 'pdf') => {
    if (!sesionId) return
    setDescargando(tipo)
    // En iPhone/Safari la pestaña debe abrirse dentro del toque (antes del await)
    const ventana = window.open('', '_blank')
    try {
      const idioma = ['es', 'en', 'zh'].includes(i18n.language) ? i18n.language : 'es'
      const blob = await descargarCotizacion(sesionId, idioma, tipo)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = `Cotizacion.${tipo === 'excel' ? 'xlsx' : 'pdf'}`
        a.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      ventana?.close()
    } finally {
      setDescargando(null)
    }
  }

  const enviarPedido = async () => {
    if (!sesionId || !detalle) return
    setEnviando(true)
    try {
      const items = detalle.items.map((it) => ({
        item_id: it.item_id,
        cantidad: Number(cantidades[it.item_id] || 0),
      }))
      await enviarPedidoPortal(sesionId, { items, notas: notas.trim() || null })
      setDetalle({ ...detalle, pedido_recibido: true, notas_cliente: notas.trim() || null })
      toast.success(t('portal.pedidoEnviado'))
    } catch {
      toast.error(t('portal.errorPedido'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <PortalLayout>
      <button
        type="button"
        onClick={() => navigate('/portal')}
        className="mb-4 flex items-center gap-1 text-sm font-medium"
        style={{ color: '#4B52E8' }}
      >
        <ArrowLeft size={16} /> {t('portal.volver')}
      </button>

      {noEncontrada ? (
        <div className="card">
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {t('portal.noEncontrada')}
          </p>
        </div>
      ) : !detalle ? (
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {t('portal.cargando')}
        </p>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Encabezado */}
          <div>
            <h1 style={{ fontWeight: 700, fontSize: 24, color: '#0D0D0D' }}>{detalle.numero}</h1>
            <p className="text-sm" style={{ color: '#6B7280' }}>
              {t('portal.productos', { n: detalle.items.length })} · {t('portal.totalEstimado')}: ${' '}
              {detalle.total_usd.toLocaleString('es-ES')}
            </p>
          </div>

          {/* Descargas */}
          <div className="card flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => descargar('pdf')}
              disabled={descargando !== null}
              className="flex flex-1 items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, fontSize: 16 }}
            >
              <FileText size={18} /> {descargando === 'pdf' ? t('cotizacion.generando') : t('portal.descargarPDF')}
            </button>
            <button
              type="button"
              onClick={() => descargar('excel')}
              disabled={descargando !== null}
              className="flex flex-1 items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 48, backgroundColor: '#10B981', borderRadius: 8, fontSize: 16 }}
            >
              <FileSpreadsheet size={18} /> {descargando === 'excel' ? t('cotizacion.generando') : t('portal.descargarExcel')}
            </button>
          </div>

          {/* Mi pedido: cajas por producto + notas */}
          <div className="card">
            <h2 className="mb-1" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
              {t('portal.miPedidoTitulo')}
            </h2>
            <p className="mb-4 text-sm" style={{ color: '#6B7280' }}>
              {t('portal.miPedidoAyuda')}
            </p>
            {detalle.pedido_recibido && (
              <p className="mb-4 rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: '#D1FAE5', color: '#065F46' }}>
                {t('portal.pedidoRecibidoAviso')}
              </p>
            )}

            <div className="flex flex-col gap-3">
              {detalle.items.map((item) => {
                const cajas = Number(cantidades[item.item_id] || 0)
                return (
                  <div key={item.item_id} className="flex flex-col gap-3 rounded-xl border border-gray-200 p-3">
                    <div className="flex gap-3">
                      {item.foto_url ? (
                        <img
                          src={item.foto_url}
                          alt=""
                          style={{ width: 64, height: 64 }}
                          className="flex-shrink-0 rounded-lg object-cover"
                        />
                      ) : (
                        <div style={{ width: 64, height: 64 }} className="flex-shrink-0 rounded-lg bg-gray-100" />
                      )}
                      <div className="min-w-0 flex-1">
                        <p className="font-medium" style={{ color: '#0D0D0D' }}>
                          {descripcion(item, i18n.language) || '—'}
                        </p>
                        <p className="text-sm" style={{ color: '#6B7280' }}>
                          {t('portal.precioUnit')}: $ {item.price_usd.toLocaleString('es-ES')}
                          {item.qty_por_ctn > 0 ? ` · ${t('portal.porCaja', { n: item.qty_por_ctn })}` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-2">
                      <label className="text-sm font-medium" style={{ color: '#374151' }}>
                        {t('portal.cajasDeseadas')}:
                      </label>
                      <input
                        type="number"
                        min={0}
                        inputMode="numeric"
                        value={cantidades[item.item_id] ?? ''}
                        onChange={(e) => setCantidades((c) => ({ ...c, [item.item_id]: e.target.value }))}
                        className="w-24 rounded-lg border border-gray-200 px-2 py-1 focus:border-[#4B52E8] focus:outline-none"
                        style={{ fontSize: 16 }}
                      />
                      {item.qty_por_ctn > 0 && cajas > 0 && (
                        <span className="text-xs" style={{ color: '#9CA3AF' }}>
                          ≈ {(cajas * item.qty_por_ctn).toLocaleString('es-ES')} {t('portal.unidades')}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>

            <label className="mt-4 flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('portal.notasLabel')}
              <textarea
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                rows={3}
                placeholder={t('portal.notasPlaceholder')}
                className="rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none"
                style={{ fontSize: 16 }}
              />
            </label>

            <button
              type="button"
              onClick={enviarPedido}
              disabled={enviando}
              className="mt-4 flex min-h-[48px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: '#4B52E8', fontSize: 16 }}
            >
              <Send size={18} />{' '}
              {enviando
                ? t('portal.enviando')
                : detalle.pedido_recibido
                  ? t('portal.actualizarPedido')
                  : t('portal.enviarPedido')}
            </button>
          </div>

          {/* Productos (resumen con totales de la cotización) */}
          <div className="card">
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
              {t('portal.productos', { n: detalle.items.length })}
            </h2>
            <div className="flex flex-col gap-3">
              {detalle.items.map((item) => (
                <div key={item.item_id} className="flex gap-3 rounded-xl border border-gray-200 p-3">
                  {item.foto_url ? (
                    <img
                      src={item.foto_url}
                      alt=""
                      style={{ width: 64, height: 64 }}
                      className="flex-shrink-0 rounded-lg object-cover"
                    />
                  ) : (
                    <div style={{ width: 64, height: 64 }} className="flex-shrink-0 rounded-lg bg-gray-100" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="font-medium" style={{ color: '#0D0D0D' }}>
                      {descripcion(item, i18n.language) || '—'}
                    </p>
                    <p className="text-sm" style={{ color: '#6B7280' }}>
                      {t('portal.cantidad')}: {item.t_qty} · {t('portal.precioUnit')}: $ {item.price_usd.toLocaleString('es-ES')}
                    </p>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <p className="font-semibold" style={{ color: '#0D0D0D' }}>
                      $ {item.total_usd.toLocaleString('es-ES')}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 flex justify-end border-t border-gray-100 pt-3">
              <p style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
                {t('portal.total')}: $ {detalle.total_usd.toLocaleString('es-ES')}
              </p>
            </div>
          </div>

          {/* Seguimiento */}
          <div className="card">
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
              {t('portal.seguimiento')}
            </h2>
            <SeguimientoTimeline seguimiento={detalle.seguimiento} />
          </div>
        </div>
      )}
    </PortalLayout>
  )
}

export default PortalDetalle
