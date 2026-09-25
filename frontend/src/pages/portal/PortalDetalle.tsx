import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock,
  FileSpreadsheet,
  FileText,
  Lock,
  Pencil,
  PlayCircle,
  Plus,
  RefreshCw,
  Send,
  Trash2,
  Truck,
  X,
} from 'lucide-react'
import PortalLayout from '../../components/portal/PortalLayout'
import SeguimientoTimeline from '../../components/portal/SeguimientoTimeline'
import {
  aprobarDespachoPortal,
  confirmarPedidoPortal,
  descargarCotizacion,
  enviarPedidoPortal,
  getCotizacionDetalle,
} from '../../api/portal'
import { confirmar as pedirConfirmacion } from '../../store/confirmStore'
import type { CotizacionDetalle, PortalItem } from '../../types/portal'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

// Desde que el pedido llega a la tienda en adelante, ya se compró físicamente
// con las cantidades que el cliente mandó -editarlas acá no cambia nada real
// y solo confunde, así que el pedido queda de solo lectura.
const ESTADOS_EN_PROCESO = ['proveedor_recibio', 'en_bodega', 'en_transito', 'en_destino', 'entregado']

function descripcion(item: PortalItem, idioma: string): string {
  if (idioma === 'en') return item.descripcion_en || item.descripcion_es || ''
  if (idioma === 'zh') return item.descripcion_zh || item.descripcion_es || ''
  return item.descripcion_es || item.descripcion_en || ''
}

interface Media {
  tipo: 'foto' | 'video'
  url: string
}

function mediaDeItem(item: PortalItem): Media[] {
  if (!item.inspeccion_bodega) return []
  const media: Media[] = item.inspeccion_bodega.fotos.map((url) => ({ tipo: 'foto' as const, url }))
  if (item.inspeccion_bodega.video_url) media.push({ tipo: 'video', url: item.inspeccion_bodega.video_url })
  return media
}

// Visor de evidencia: fotos/video de un producto, en la misma página (sin
// abrir pestañas), con flechas para pasar entre ellas y el contexto del
// producto (y lo que reportó bodega) debajo.
function VisorEvidencia({
  item,
  indiceInicial,
  idioma,
  onCerrar,
}: {
  item: PortalItem
  indiceInicial: number
  idioma: string
  onCerrar: () => void
}) {
  const { t } = useTranslation()
  const media = mediaDeItem(item)
  const [indice, setIndice] = useState(indiceInicial)
  // Zoom simple sobre la foto (no aplica a video): un toque la amplía, otro
  // la vuelve a su tamaño. Se resetea al cambiar de foto.
  const [zoom, setZoom] = useState(false)
  const actual = media[indice]
  const insp = item.inspeccion_bodega

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCerrar()
      if (e.key === 'ArrowLeft') setIndice((i) => (i - 1 + media.length) % media.length)
      if (e.key === 'ArrowRight') setIndice((i) => (i + 1) % media.length)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [media.length])

  useEffect(() => {
    setZoom(false)
  }, [indice])

  if (!actual || !insp) return null

  const descCorregida = idioma === 'en' ? insp.descripcion_en : insp.descripcion_es

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col bg-black/90 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onCerrar}
    >
      <button
        type="button"
        onClick={onCerrar}
        aria-label={t('portal.cerrar')}
        className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-full bg-black/40 text-white"
      >
        <X size={22} />
      </button>

      <div className="flex flex-1 items-center justify-center gap-2" onClick={(e) => e.stopPropagation()}>
        {media.length > 1 && (
          <button
            type="button"
            onClick={() => setIndice((i) => (i - 1 + media.length) % media.length)}
            aria-label={t('portal.anterior')}
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-black/40 text-white"
          >
            <ChevronLeft size={24} />
          </button>
        )}

        <div className="flex max-h-full max-w-full flex-1 items-center justify-center overflow-auto">
          {actual.tipo === 'foto' ? (
            <img
              src={actual.url}
              alt=""
              onClick={(e) => {
                e.stopPropagation()
                setZoom((z) => !z)
              }}
              className="rounded-lg object-contain transition-transform"
              style={
                zoom
                  ? { maxHeight: 'none', maxWidth: 'none', width: 'auto', height: 'auto', transform: 'scale(2)', cursor: 'zoom-out' }
                  : { maxHeight: '70vh', maxWidth: '100%', cursor: 'zoom-in' }
              }
            />
          ) : (
            <video src={actual.url} controls autoPlay className="max-h-[70vh] max-w-full rounded-lg" />
          )}
        </div>

        {media.length > 1 && (
          <button
            type="button"
            onClick={() => setIndice((i) => (i + 1) % media.length)}
            aria-label={t('portal.siguiente')}
            className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-black/40 text-white"
          >
            <ChevronRight size={24} />
          </button>
        )}
      </div>

      <div
        className="mx-auto w-full max-w-lg rounded-xl bg-white p-4"
        onClick={(e) => e.stopPropagation()}
      >
        {item.referencia && (
          <p className="text-xs font-semibold tracking-wide" style={{ color: 'var(--yuda-primary)' }}>
            {item.referencia}
          </p>
        )}
        <p className="font-medium" style={{ color: 'var(--yuda-accent)' }}>
          {descripcion(item, idioma) || '—'}
        </p>
        <div className="mt-2 border-t border-gray-100 pt-2">
          <p
            className="mb-1 flex items-center gap-2 text-xs font-semibold"
            style={{
              color: insp.referencia_coincide === false ? 'var(--yuda-warning-dark)' : 'var(--yuda-success-dark)',
            }}
          >
            {insp.referencia_coincide === false ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
            {t('portal.inspeccionTitulo')}
            {' · '}
            {insp.referencia_coincide === false
              ? t('portal.inspeccionNoCoincide')
              : insp.referencia_coincide === true
                ? t('portal.inspeccionCoincide')
                : ''}
          </p>
          {insp.ctns != null && insp.ctns !== item.ctns && (
            <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('portal.inspeccionCantidadEncontrada', { n: insp.ctns, original: item.ctns })}
            </p>
          )}
          {descCorregida && (
            <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('portal.inspeccionDescripcionEncontrada', { texto: descCorregida })}
            </p>
          )}
        </div>
        {media.length > 1 && (
          <p className="mt-2 text-center text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
            {indice + 1} / {media.length}
          </p>
        )}
      </div>
    </div>
  )
}

function PortalDetalle() {
  const { sesionId } = useParams<{ sesionId: string }>()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const [detalle, setDetalle] = useState<CotizacionDetalle | null>(null)
  const [cargando, setCargando] = useState(true)
  const [noEncontrada, setNoEncontrada] = useState(false)
  const [errorCarga, setErrorCarga] = useState(false)
  const [descargando, setDescargando] = useState<'excel' | 'pdf' | null>(null)
  // Pedido del cliente: cajas por producto (item_id -> texto) y notas.
  const [cantidades, setCantidades] = useState<Record<string, string>>({})
  // Productos que el cliente quitó de su pedido en esta edición (no compra
  // nada al servidor: solo pone la cantidad en 0, pero acá sirve para mostrar
  // la tarjeta "quitado" en vez del editor de cantidad).
  const [quitados, setQuitados] = useState<Set<string>>(new Set())
  // Total en vivo según las cajas que el cliente va pidiendo: detalle.total_usd
  // es el total de la cotización ORIGINAL (con las cantidades que se cotizaron),
  // y no cambiaba si el cliente ajustaba cuántas cajas quería de cada producto
  // o quitaba alguno -"Total estimado" se quedaba fijo aunque el pedido real
  // ya fuera otro.
  const totalEnVivo = useMemo(() => {
    if (!detalle) return 0
    return detalle.items.reduce((acc, it) => {
      if (quitados.has(it.item_id)) return acc
      const cajas = Number(cantidades[it.item_id] || 0)
      return acc + cajas * it.qty_por_ctn * it.price_usd
    }, 0)
  }, [detalle, cantidades, quitados])
  const [notas, setNotas] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [aprobando, setAprobando] = useState(false)
  // Para modificar un pedido ya confirmado hace falta una acción explícita.
  const [editando, setEditando] = useState(false)
  // Visor de evidencia (fotos/video) de un producto: qué item y en qué índice
  // de su galería se abrió.
  const [visor, setVisor] = useState<{ itemId: string; indice: number } | null>(null)
  // Aprobación del despacho producto por producto: qué productos ya marcó el
  // cliente y qué observación dejó en cada uno (opcional). La aprobación
  // sigue siendo de todo el pedido junto -no se manda hasta marcar el 100%-,
  // pero cada observación va aparte para que bodega sepa a cuál producto se
  // refiere.
  const [aprobadosItems, setAprobadosItems] = useState<Set<string>>(new Set())
  const [observacionesItems, setObservacionesItems] = useState<Record<string, string>>({})

  const cargar = useCallback(() => {
    if (!sesionId) return
    setCargando(true)
    setNoEncontrada(false)
    setErrorCarga(false)
    getCotizacionDetalle(sesionId)
      .then((d) => {
        setDetalle(d)
        const init: Record<string, string> = {}
        d.items.forEach((it) => {
          if (it.cantidad_solicitada != null) init[it.item_id] = String(it.cantidad_solicitada)
        })
        setCantidades(init)
        setQuitados(new Set())
        setNotas(d.notas_cliente ?? '')
      })
      .catch((err) => {
        // Distinguir "no existe" (404) de un error de red/servidor.
        if (axios.isAxiosError(err) && err.response?.status === 404) setNoEncontrada(true)
        else setErrorCarga(true)
      })
      .finally(() => setCargando(false))
  }, [sesionId])

  useEffect(() => {
    cargar()
  }, [cargar])

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
      toast.error(t('portal.errorDescarga'))
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
      // Proponer cantidades (o cambios) devuelve el pedido a "recibido".
      setDetalle({
        ...detalle,
        pedido_recibido: true,
        pedido_estado: 'recibido',
        pedido_confirmado: false,
        notas_cliente: notas.trim() || null,
      })
      setEditando(false)
      toast.success(t('portal.pedidoEnviado'))
    } catch {
      toast.error(t('portal.errorPedido'))
    } finally {
      setEnviando(false)
    }
  }

  const confirmar = async () => {
    if (!sesionId || !detalle) return
    setConfirmando(true)
    try {
      await confirmarPedidoPortal(sesionId)
      setDetalle({ ...detalle, pedido_estado: 'confirmado', pedido_confirmado: true })
      toast.success(t('portal.pedidoConfirmado'))
    } catch {
      toast.error(t('portal.errorConfirmar'))
    } finally {
      setConfirmando(false)
    }
  }

  const aprobarDespacho = async () => {
    if (!sesionId || !detalle) return
    const itemsConInspeccion = detalle.items.filter((i) => i.inspeccion_bodega)
    if (itemsConInspeccion.some((i) => !aprobadosItems.has(i.item_id))) return
    setAprobando(true)
    try {
      const observaciones = itemsConInspeccion
        .map((i) => ({ item_id: i.item_id, texto: (observacionesItems[i.item_id] ?? '').trim() }))
        .filter((o) => o.texto.length > 0)
      await aprobarDespachoPortal(sesionId, observaciones)
      setDetalle({
        ...detalle,
        seguimiento: { ...detalle.seguimiento, cliente_aprobo_despacho_at: new Date().toISOString() },
      })
      toast.success(t('portal.despachoAprobado'))
    } catch (err) {
      const mensaje =
        (axios.isAxiosError(err) && err.response?.data?.detail) || t('portal.errorAprobarDespacho')
      toast.error(mensaje)
    } finally {
      setAprobando(false)
    }
  }

  const alternarAprobadoItem = (itemId: string) => {
    setAprobadosItems((prev) => {
      const copia = new Set(prev)
      if (copia.has(itemId)) copia.delete(itemId)
      else copia.add(itemId)
      return copia
    })
  }

  // Pedir confirmación explícita antes de reabrir un pedido ya confirmado.
  const modificarConfirmado = async () => {
    if (await pedirConfirmacion(t('portal.avisoModificar'))) setEditando(true)
  }

  const confirmado = detalle?.pedido_estado === 'confirmado'
  // Desde que el pedido ya está en proceso con el proveedor (o más allá), ya
  // se compró con estas cantidades: no hay "Modificar pedido" que valga.
  const enProceso = !!detalle && ESTADOS_EN_PROCESO.includes(detalle.seguimiento.estado)
  // Con el pedido confirmado los campos quedan bloqueados hasta "Modificar pedido".
  const bloqueado = enProceso || (confirmado && !editando)

  return (
    <PortalLayout>
      <button
        type="button"
        onClick={() => navigate('/portal')}
        className="mb-4 flex items-center gap-1 text-sm font-medium"
        style={{ color: 'var(--yuda-primary)' }}
      >
        <ArrowLeft size={16} /> {t('portal.volver')}
      </button>

      {cargando ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('portal.cargando')}
        </p>
      ) : errorCarga ? (
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
      ) : noEncontrada || !detalle ? (
        <div className="card">
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('portal.noEncontrada')}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {/* Encabezado */}
          <div>
            <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>{detalle.numero}</h1>
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('portal.productos', { n: detalle.items.length })} · {t('portal.totalEstimado')}: US${' '}
              {totalEnVivo.toLocaleString('es-ES')}
            </p>
          </div>

          {/* Descargas */}
          <div className="card flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={() => descargar('pdf')}
              disabled={descargando !== null}
              className="flex flex-1 items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 48, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, fontSize: 16 }}
            >
              <FileText size={18} /> {descargando === 'pdf' ? t('cotizacion.generando') : t('portal.descargarPDF')}
            </button>
            <button
              type="button"
              onClick={() => descargar('excel')}
              disabled={descargando !== null}
              className="flex flex-1 items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 48, backgroundColor: 'var(--yuda-success)', borderRadius: 8, fontSize: 16 }}
            >
              <FileSpreadsheet size={18} /> {descargando === 'excel' ? t('cotizacion.generando') : t('portal.descargarExcel')}
            </button>
          </div>

          {/* Mi pedido: cajas por producto + notas */}
          <div className="card">
            <h2 className="mb-1" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
              {t('portal.miPedidoTitulo')}
            </h2>
            <p className="mb-4 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('portal.miPedidoAyuda')}
            </p>
            {enProceso ? (
              <p className="mb-4 flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: 'var(--yuda-bg)', color: 'var(--yuda-text-secondary)' }}>
                <Lock size={16} /> {t('portal.pedidoEnProceso')}
              </p>
            ) : (
              <>
                {detalle.pedido_estado === 'por_confirmar' && (
                  <p className="mb-4 rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}>
                    {t('portal.porConfirmarAviso')}
                  </p>
                )}
                {detalle.pedido_estado === 'confirmado' && (
                  <p className="mb-4 flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }}>
                    <CheckCircle2 size={16} /> {t('portal.confirmadoAviso')}
                  </p>
                )}
                {detalle.pedido_estado === 'recibido' && (
                  <p className="mb-4 rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}>
                    {t('portal.pedidoRecibidoAviso')}
                  </p>
                )}
              </>
            )}

            <div className="flex flex-col gap-3">
              {detalle.items.map((item) => {
                const cajas = Number(cantidades[item.item_id] || 0)
                const quitado = quitados.has(item.item_id)

                const quitar = () => {
                  setQuitados((q) => new Set(q).add(item.item_id))
                  setCantidades((c) => ({ ...c, [item.item_id]: '0' }))
                }
                const readmitir = () => {
                  setQuitados((q) => {
                    const copia = new Set(q)
                    copia.delete(item.item_id)
                    return copia
                  })
                  setCantidades((c) => ({ ...c, [item.item_id]: '1' }))
                }

                return (
                  <div
                    key={item.item_id}
                    className="flex flex-col gap-3 rounded-xl border p-3"
                    style={{ borderColor: 'var(--yuda-border)', opacity: quitado ? 0.6 : 1 }}
                  >
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
                        {item.referencia && (
                          <p className="text-xs font-semibold tracking-wide" style={{ color: 'var(--yuda-primary)' }}>
                            {item.referencia}
                          </p>
                        )}
                        <p className="font-medium" style={{ color: 'var(--yuda-accent)' }}>
                          {descripcion(item, i18n.language) || '—'}
                        </p>
                        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                          {t('portal.precioUnit')}: US$ {item.price_usd.toLocaleString('es-ES')}
                          {item.qty_por_ctn > 0 ? ` · ${t('portal.porCaja', { n: item.qty_por_ctn })}` : ''}
                        </p>
                      </div>
                      {!bloqueado &&
                        (quitado ? (
                          <button
                            type="button"
                            onClick={readmitir}
                            className="flex flex-shrink-0 items-center gap-1 self-start rounded-lg border px-2 py-1 text-xs font-semibold"
                            style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)' }}
                          >
                            <Plus size={14} /> {t('portal.readmitirProducto')}
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={quitar}
                            aria-label={t('portal.quitarProducto')}
                            className="flex flex-shrink-0 items-center self-start rounded-lg p-2"
                            style={{ color: 'var(--yuda-text-secondary)' }}
                          >
                            <Trash2 size={16} />
                          </button>
                        ))}
                    </div>
                    {quitado ? (
                      <p
                        className="rounded-lg border-t border-gray-100 pt-2 text-sm font-medium"
                        style={{ color: 'var(--yuda-text-secondary)' }}
                      >
                        {t('portal.productoQuitado')}
                      </p>
                    ) : (
                      <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-2">
                        <label className="text-sm font-medium" style={{ color: 'var(--yuda-text)' }}>
                          {t('portal.cajasDeseadas')}:
                        </label>
                        <input
                          type="number"
                          min={0}
                          inputMode="numeric"
                          value={cantidades[item.item_id] ?? ''}
                          onChange={(e) => setCantidades((c) => ({ ...c, [item.item_id]: e.target.value }))}
                          disabled={bloqueado}
                          className="min-h-[44px] w-24 rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
                          style={{ fontSize: 16 }}
                        />
                        {item.qty_por_ctn > 0 && cajas > 0 && (
                          <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                            ≈ {(cajas * item.qty_por_ctn).toLocaleString('es-ES')} {t('portal.unidades')}
                          </span>
                        )}
                      </div>
                    )}
                    {item.inspeccion_bodega && (
                      <div className="border-t border-gray-100 pt-2">
                        <p
                          className="mb-2 flex items-center gap-2 text-xs font-semibold"
                          style={{
                            color:
                              item.inspeccion_bodega.referencia_coincide === false
                                ? 'var(--yuda-warning-dark)'
                                : 'var(--yuda-success-dark)',
                          }}
                        >
                          {item.inspeccion_bodega.referencia_coincide === false ? (
                            <AlertTriangle size={14} />
                          ) : (
                            <CheckCircle2 size={14} />
                          )}
                          {t('portal.inspeccionTitulo')}
                          {' · '}
                          {item.inspeccion_bodega.referencia_coincide === false
                            ? t('portal.inspeccionNoCoincide')
                            : item.inspeccion_bodega.referencia_coincide === true
                              ? t('portal.inspeccionCoincide')
                              : ''}
                        </p>
                        <div className="mb-2 flex flex-wrap gap-2">
                          {item.inspeccion_bodega.fotos.map((url, i) => (
                            <button
                              key={url}
                              type="button"
                              onClick={() => setVisor({ itemId: item.item_id, indice: i })}
                            >
                              <img
                                src={url}
                                alt=""
                                style={{ width: 56, height: 56 }}
                                className="rounded-lg object-cover"
                              />
                            </button>
                          ))}
                          {item.inspeccion_bodega.video_url && (
                            <button
                              type="button"
                              onClick={() =>
                                setVisor({ itemId: item.item_id, indice: item.inspeccion_bodega!.fotos.length })
                              }
                              style={{ width: 56, height: 56, backgroundColor: 'var(--yuda-bg)' }}
                              className="flex flex-shrink-0 items-center justify-center rounded-lg"
                              aria-label={t('portal.inspeccionVerVideo')}
                            >
                              <PlayCircle size={22} color="var(--yuda-primary)" />
                            </button>
                          )}
                        </div>
                        {item.inspeccion_bodega.ctns != null && item.inspeccion_bodega.ctns !== item.ctns && (
                          <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                            {t('portal.inspeccionCantidadEncontrada', {
                              n: item.inspeccion_bodega.ctns,
                              original: item.ctns,
                            })}
                          </p>
                        )}
                        {(() => {
                          const desc =
                            i18n.language === 'en'
                              ? item.inspeccion_bodega.descripcion_en
                              : item.inspeccion_bodega.descripcion_es
                          return desc ? (
                            <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                              {t('portal.inspeccionDescripcionEncontrada', { texto: desc })}
                            </p>
                          ) : null
                        })()}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            <div className="mt-3 flex justify-end border-t border-gray-100 pt-3">
              <p style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
                {t('portal.totalEstimado')}: US$ {totalEnVivo.toLocaleString('es-ES')}
              </p>
            </div>

            <label className="mt-4 flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('portal.notasLabel')}
              <textarea
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                rows={3}
                placeholder={t('portal.notasPlaceholder')}
                disabled={bloqueado}
                className="rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
                style={{ fontSize: 16 }}
              />
            </label>

            {enProceso ? null : detalle.pedido_estado === 'por_confirmar' ? (
              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={confirmar}
                  disabled={confirmando || enviando}
                  className="flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-success)', fontSize: 16 }}
                >
                  <CheckCircle2 size={18} /> {confirmando ? t('portal.confirmando') : t('portal.confirmarPedido')}
                </button>
                <button
                  type="button"
                  onClick={enviarPedido}
                  disabled={enviando || confirmando}
                  className="flex min-h-[48px] flex-1 items-center justify-center gap-2 rounded-lg border font-semibold disabled:opacity-60"
                  style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)', fontSize: 16 }}
                >
                  <Send size={18} /> {enviando ? t('portal.enviando') : t('portal.proponerCambios')}
                </button>
              </div>
            ) : confirmado && !editando ? (
              <button
                type="button"
                onClick={modificarConfirmado}
                className="mt-4 flex min-h-[48px] w-full items-center justify-center gap-2 rounded-lg border font-semibold"
                style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)', fontSize: 16 }}
              >
                <Pencil size={18} /> {t('portal.modificarPedido')}
              </button>
            ) : (
              <button
                type="button"
                onClick={enviarPedido}
                disabled={enviando}
                className="mt-4 flex min-h-[48px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 16 }}
              >
                <Send size={18} />{' '}
                {enviando
                  ? t('portal.enviando')
                  : editando
                    ? t('portal.enviarCambios')
                    : detalle.pedido_recibido
                      ? t('portal.actualizarPedido')
                      : t('portal.enviarPedido')}
              </button>
            )}
          </div>

          {/* Seguimiento */}
          <div className="card">
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
              {t('portal.seguimiento')}
            </h2>

            {detalle.seguimiento.estado === 'en_bodega' && (() => {
              const aprobado = !!detalle.seguimiento.cliente_aprobo_despacho_at
              const limite = detalle.seguimiento.aprobacion_limite_at
              const vencido = !!limite && new Date(limite).getTime() < Date.now()
              const locale = LOCALES[i18n.language] || 'es-ES'
              const fechaLimite = limite
                ? new Date(limite).toLocaleString(locale, {
                    day: 'numeric',
                    month: 'long',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : null
              const itemsConInspeccion = detalle.items.filter((i) => i.inspeccion_bodega)
              const todosSeleccionados =
                itemsConInspeccion.length > 0 && itemsConInspeccion.every((i) => aprobadosItems.has(i.item_id))
              const seleccionarTodos = () =>
                setAprobadosItems(todosSeleccionados ? new Set() : new Set(itemsConInspeccion.map((i) => i.item_id)))

              return (
                <div
                  className="mb-4 rounded-xl p-4"
                  style={{
                    backgroundColor: aprobado
                      ? 'var(--yuda-success-soft)'
                      : vencido
                        ? 'var(--yuda-warning-soft)'
                        : 'var(--yuda-primary-soft)',
                  }}
                >
                  {aprobado ? (
                    <p
                      className="flex items-center gap-2 text-sm font-semibold"
                      style={{ color: 'var(--yuda-success-dark)' }}
                    >
                      <CheckCircle2 size={18} /> {t('portal.despachoYaAprobado')}
                    </p>
                  ) : (
                    <>
                      <p
                        className="mb-1 flex items-center gap-2 text-sm font-semibold"
                        style={{ color: vencido ? 'var(--yuda-warning-dark)' : 'var(--yuda-primary)' }}
                      >
                        <Truck size={18} /> {t('portal.aprobarDespachoTitulo')}
                      </p>
                      <p className="mb-3 text-sm" style={{ color: 'var(--yuda-text)' }}>
                        {t('portal.aprobarDespachoAyuda')}
                      </p>
                      {fechaLimite && !vencido && (
                        <p
                          className="mb-3 flex items-center gap-2 text-xs font-medium"
                          style={{ color: 'var(--yuda-text-secondary)' }}
                        >
                          <Clock size={14} /> {t('portal.plazoHasta', { fecha: fechaLimite })}
                        </p>
                      )}
                      {vencido && (
                        <p
                          className="mb-3 flex items-center gap-2 text-xs font-medium"
                          style={{ color: 'var(--yuda-warning-dark)' }}
                        >
                          <AlertTriangle size={14} /> {t('portal.plazoVencido')}
                        </p>
                      )}

                      {!vencido && itemsConInspeccion.length > 0 && (
                        <>
                          <div className="mb-2 flex items-center justify-between">
                            <p className="text-xs font-semibold" style={{ color: 'var(--yuda-text-secondary)' }}>
                              {t('portal.aprobarProgreso', { n: aprobadosItems.size, total: itemsConInspeccion.length })}
                            </p>
                            <button
                              type="button"
                              onClick={seleccionarTodos}
                              className="text-xs font-semibold"
                              style={{ color: 'var(--yuda-primary)' }}
                            >
                              {todosSeleccionados ? t('portal.deseleccionarTodos') : t('portal.seleccionarTodos')}
                            </button>
                          </div>
                          <div className="mb-3 flex flex-col gap-3">
                            {itemsConInspeccion.map((item) => {
                              const media = mediaDeItem(item)
                              const marcado = aprobadosItems.has(item.item_id)
                              return (
                                <div
                                  key={item.item_id}
                                  className="rounded-lg border bg-white p-3"
                                  style={{ borderColor: marcado ? 'var(--yuda-success)' : 'var(--yuda-border)' }}
                                >
                                  <label className="flex items-start gap-2">
                                    <input
                                      type="checkbox"
                                      checked={marcado}
                                      onChange={() => alternarAprobadoItem(item.item_id)}
                                      className="mt-1 flex-shrink-0"
                                      style={{ width: 18, height: 18 }}
                                    />
                                    <div className="min-w-0 flex-1">
                                      {item.referencia && (
                                        <p className="text-xs font-semibold" style={{ color: 'var(--yuda-primary)' }}>
                                          {item.referencia}
                                        </p>
                                      )}
                                      <p className="text-sm font-medium" style={{ color: 'var(--yuda-accent)' }}>
                                        {descripcion(item, i18n.language) || '—'}
                                      </p>
                                    </div>
                                  </label>
                                  {media.length > 0 && (
                                    <div className="mb-2 mt-2 flex flex-wrap gap-2">
                                      {media.map((m, i) =>
                                        m.tipo === 'foto' ? (
                                          <button
                                            key={m.url}
                                            type="button"
                                            onClick={() => setVisor({ itemId: item.item_id, indice: i })}
                                          >
                                            <img
                                              src={m.url}
                                              alt=""
                                              style={{ width: 56, height: 56 }}
                                              className="rounded-lg object-cover"
                                            />
                                          </button>
                                        ) : (
                                          <button
                                            key={m.url}
                                            type="button"
                                            onClick={() => setVisor({ itemId: item.item_id, indice: i })}
                                            style={{ width: 56, height: 56, backgroundColor: 'var(--yuda-bg)' }}
                                            className="flex flex-shrink-0 items-center justify-center rounded-lg"
                                            aria-label={t('portal.inspeccionVerVideo')}
                                          >
                                            <PlayCircle size={22} color="var(--yuda-primary)" />
                                          </button>
                                        ),
                                      )}
                                    </div>
                                  )}
                                  <textarea
                                    value={observacionesItems[item.item_id] ?? ''}
                                    onChange={(e) =>
                                      setObservacionesItems((o) => ({ ...o, [item.item_id]: e.target.value }))
                                    }
                                    placeholder={t('portal.observacionPlaceholder')}
                                    rows={2}
                                    className="w-full resize-y rounded-lg border px-2 py-1.5 text-sm focus:border-[var(--yuda-primary)] focus:outline-none"
                                    style={{ borderColor: 'var(--yuda-border)' }}
                                  />
                                </div>
                              )
                            })}
                          </div>
                        </>
                      )}

                      <button
                        type="button"
                        onClick={aprobarDespacho}
                        disabled={aprobando || vencido || !todosSeleccionados}
                        className="flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-50"
                        style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 15 }}
                      >
                        <CheckCircle2 size={16} />{' '}
                        {aprobando ? t('portal.aprobando') : t('portal.aprobarDespachoBoton')}
                      </button>
                    </>
                  )}
                </div>
              )
            })()}

            {/* Fecha estimada que dio cada proveedor. Es por proveedor, no
                una sola para todo el pedido: si se reparte entre varios,
                cada uno puede tener la suya. */}
            {detalle.pedidos_generados.some((pg) => pg.fecha_tentativa_entrega) && (
              <div className="mb-5 rounded-xl p-4" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
                <p className="mb-2 flex items-center gap-2 text-sm font-semibold" style={{ color: 'var(--yuda-primary)' }}>
                  <Truck size={16} /> {t('portal.fechasEstimadasTitulo')}
                </p>
                <div className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text)' }}>
                  {detalle.pedidos_generados
                    .filter((pg) => pg.fecha_tentativa_entrega)
                    .map((pg) => (
                      <p key={pg.supplier}>
                        <strong>{pg.supplier.replace('_', ' · ')}:</strong>{' '}
                        {new Date(`${pg.fecha_tentativa_entrega}T00:00:00`).toLocaleDateString(
                          LOCALES[i18n.language] || 'es-ES',
                          { day: 'numeric', month: 'long', year: 'numeric' },
                        )}
                      </p>
                    ))}
                </div>
              </div>
            )}

            <SeguimientoTimeline seguimiento={detalle.seguimiento} />
          </div>
        </div>
      )}

      {visor &&
        (() => {
          const item = detalle?.items.find((i) => i.item_id === visor.itemId)
          if (!item) return null
          return (
            <VisorEvidencia
              item={item}
              indiceInicial={visor.indice}
              idioma={i18n.language}
              onCerrar={() => setVisor(null)}
            />
          )
        })()}
    </PortalLayout>
  )
}

export default PortalDetalle
