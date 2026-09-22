import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { AlertTriangle, ArrowLeft, CheckCircle2, Clock, FileSpreadsheet, FileText, Pencil, PlayCircle, Plus, RefreshCw, Send, Trash2, Truck } from 'lucide-react'
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
  const [notas, setNotas] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [confirmando, setConfirmando] = useState(false)
  const [aprobando, setAprobando] = useState(false)
  // Para modificar un pedido ya confirmado hace falta una acción explícita.
  const [editando, setEditando] = useState(false)

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
    setAprobando(true)
    try {
      await aprobarDespachoPortal(sesionId)
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

  // Pedir confirmación explícita antes de reabrir un pedido ya confirmado.
  const modificarConfirmado = async () => {
    if (await pedirConfirmacion(t('portal.avisoModificar'))) setEditando(true)
  }

  const confirmado = detalle?.pedido_estado === 'confirmado'
  // Con el pedido confirmado los campos quedan bloqueados hasta "Modificar pedido".
  const bloqueado = confirmado && !editando

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
                  </div>
                )
              })}
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

            {detalle.pedido_estado === 'por_confirmar' ? (
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

          {/* Productos (resumen con totales de la cotización) */}
          <div className="card">
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
              {t('portal.productos', { n: detalle.items.length })}
            </h2>
            <div className="flex flex-col gap-3">
              {detalle.items.map((item) => (
                <div key={item.item_id} className="flex flex-col rounded-xl border border-gray-200 p-3">
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
                        {t('portal.cantidad')}: {item.t_qty} · {t('portal.precioUnit')}: US$ {item.price_usd.toLocaleString('es-ES')}
                      </p>
                    </div>
                    <div className="flex-shrink-0 text-right">
                      <p className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                        US$ {item.total_usd.toLocaleString('es-ES')}
                      </p>
                    </div>
                  </div>
                  {item.inspeccion_bodega && (
                    <div className="mt-2 rounded-lg border-t border-gray-100 pt-2">
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
                      {item.inspeccion_bodega.fotos.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-2">
                          {item.inspeccion_bodega.fotos.map((url) => (
                            <a key={url} href={url} target="_blank" rel="noreferrer">
                              <img
                                src={url}
                                alt=""
                                style={{ width: 56, height: 56 }}
                                className="rounded-lg object-cover"
                              />
                            </a>
                          ))}
                        </div>
                      )}
                      {item.inspeccion_bodega.video_url && (
                        <a
                          href={item.inspeccion_bodega.video_url}
                          target="_blank"
                          rel="noreferrer"
                          className="mb-2 flex items-center gap-1 text-xs font-semibold"
                          style={{ color: 'var(--yuda-primary)' }}
                        >
                          <PlayCircle size={14} /> {t('portal.inspeccionVerVideo')}
                        </a>
                      )}
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
              ))}
            </div>
            <div className="mt-4 flex justify-end border-t border-gray-100 pt-3">
              <p style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
                {t('portal.total')}: US$ {detalle.total_usd.toLocaleString('es-ES')}
              </p>
            </div>
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
                      <button
                        type="button"
                        onClick={aprobarDespacho}
                        disabled={aprobando || vencido}
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
    </PortalLayout>
  )
}

export default PortalDetalle
