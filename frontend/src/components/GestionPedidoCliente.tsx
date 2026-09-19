import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { CheckCircle2, Clock, FileSpreadsheet, Package, Send, Warehouse } from 'lucide-react'
import { getItems } from '../api/packing'
import { enviarAConfirmar, getSeguimiento, guardarSeguimiento } from '../api/clientes'
import { actualizarFechaTentativa, getPedidos } from '../api/pedidos'
import GenerarPedidos from './GenerarPedidos/GenerarPedidos'
import type { ItemResponse, Sesion } from '../types/packing'
import type { PedidoGenerado } from '../types/pedidos'
import type { Seguimiento } from '../types/seguimiento'

// Gestión del pedido del cliente en el perfil del cliente (vendedora/Marcela):
// muestra las cantidades que pidió el cliente, permite ajustarlas y devolvérselas
// para confirmar, y —una vez confirmado— generar el pedido al proveedor.
function GestionPedidoCliente({ sesion, onActualizar }: { sesion: Sesion; onActualizar?: () => void }) {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState<ItemResponse[]>([])
  const [cantidades, setCantidades] = useState<Record<string, string>>({})
  const [estado, setEstado] = useState<string | null>(sesion.pedido_estado ?? null)
  const [enviando, setEnviando] = useState(false)
  const [seguimiento, setSeguimiento] = useState<Seguimiento | null>(null)
  const [enviandoABodega, setEnviandoABodega] = useState(false)
  const [pedidosGenerados, setPedidosGenerados] = useState<PedidoGenerado[]>([])
  const [editandoFecha, setEditandoFecha] = useState<Record<string, boolean>>({})
  const [fechaInput, setFechaInput] = useState<Record<string, string>>({})
  const [guardandoFecha, setGuardandoFecha] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (!sesion.pedido_recibido_at) return
    getItems(sesion.id)
      .then((its) => {
        setItems(its)
        const init: Record<string, string> = {}
        its.forEach((it) => {
          if (it.cantidad_solicitada != null) init[it.id] = String(it.cantidad_solicitada)
        })
        setCantidades(init)
      })
      .catch(() => setItems([]))
    getSeguimiento(sesion.id).then(setSeguimiento)
    getPedidos(sesion.id).then(setPedidosGenerados).catch(() => setPedidosGenerados([]))
  }, [sesion.id, sesion.pedido_recibido_at])

  if (!sesion.pedido_recibido_at) return null

  const descripcion = (it: ItemResponse): string =>
    (i18n.language === 'en' ? it.descripcion_en || it.descripcion_es : it.descripcion_es || it.descripcion_en) ||
    it.item_no ||
    '—'

  const confirmado = estado === 'confirmado'
  const porConfirmar = estado === 'por_confirmar'

  const badge = confirmado
    ? { txt: t('gestionPedido.estadoConfirmado'), bg: 'var(--yuda-success-soft)', fg: 'var(--yuda-success-dark)', icon: <CheckCircle2 size={13} /> }
    : porConfirmar
      ? { txt: t('gestionPedido.estadoPorConfirmar'), bg: 'var(--yuda-warning-soft)', fg: 'var(--yuda-warning-dark)', icon: <Clock size={13} /> }
      : { txt: t('gestionPedido.estadoRecibido'), bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)', icon: <Package size={13} /> }

  const enviar = async () => {
    setEnviando(true)
    try {
      const payload = items.map((it) => ({ item_id: it.id, cantidad: Number(cantidades[it.id] || 0) }))
      const s = await enviarAConfirmar(sesion.id, payload)
      setEstado(s.pedido_estado ?? 'por_confirmar')
      toast.success(t('gestionPedido.enviadoAConfirmar'))
      onActualizar?.()
    } catch {
      toast.error(t('gestionPedido.error'))
    } finally {
      setEnviando(false)
    }
  }

  // Le avisa a bodega que ya puede revisar este pedido: mueve el seguimiento a
  // "proveedor_recibio" (donde Yuda Logistic lo recoge), sin tocar el resto de
  // los campos ya guardados (novedades, tracking, etc.).
  const enviarABodega = async () => {
    setEnviandoABodega(true)
    try {
      const actualizado = await guardarSeguimiento(sesion.id, {
        estado: 'proveedor_recibio',
        novedades: seguimiento?.novedades ?? null,
        numero_tracking: seguimiento?.numero_tracking ?? null,
        naviera: seguimiento?.naviera ?? null,
        url_tracking: seguimiento?.url_tracking ?? null,
        fecha_eta: seguimiento?.fecha_eta ?? null,
        bl_numero: seguimiento?.bl_numero ?? null,
        bl_pdf_url: seguimiento?.bl_pdf_url ?? null,
        monto_venta: seguimiento?.monto_venta ?? null,
        hitos: seguimiento?.hitos ?? undefined,
      })
      setSeguimiento(actualizado)
      toast.success(t('gestionPedido.enviadoABodega'))
    } catch {
      toast.error(t('gestionPedido.errorEnviarABodega'))
    } finally {
      setEnviandoABodega(false)
    }
  }

  // Fecha aproximada que dio ESTE proveedor (por eso va por pg.id, no una
  // sola para toda la cotización: cada proveedor puede tener la suya).
  const guardarFechaTentativa = async (pg: PedidoGenerado) => {
    const fecha = fechaInput[pg.id]
    if (!fecha) return
    setGuardandoFecha((s) => ({ ...s, [pg.id]: true }))
    try {
      const actualizado = await actualizarFechaTentativa(pg.id, fecha)
      setPedidosGenerados((lista) => lista.map((p) => (p.id === pg.id ? actualizado : p)))
      setEditandoFecha((s) => ({ ...s, [pg.id]: false }))
      toast.success(t('gestionPedido.fechaTentativaGuardada'))
    } catch {
      toast.error(t('gestionPedido.errorFechaTentativa'))
    } finally {
      setGuardandoFecha((s) => ({ ...s, [pg.id]: false }))
    }
  }

  return (
    <div className="rounded-xl border" style={{ borderColor: '#C7CBF7', backgroundColor: '#F5F6FE' }}>
      {/* Encabezado + estado */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5" style={{ borderColor: '#E0E2FA' }}>
        <p className="flex items-center gap-2 text-sm font-bold" style={{ color: 'var(--yuda-primary)' }}>
          <Package size={16} /> {t('gestionPedido.titulo')}
        </p>
        <span
          className="flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ backgroundColor: badge.bg, color: badge.fg }}
        >
          {badge.icon} {badge.txt}
        </span>
      </div>

      {/* Cantidades por producto (editables salvo cuando ya está confirmado) */}
      <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
        {items.map((it) => (
          <div key={it.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
            <span className="min-w-0 flex-1" style={{ color: 'var(--yuda-accent)' }}>{descripcion(it)}</span>
            {confirmado ? (
              <span className="flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold text-white" style={{ backgroundColor: 'var(--yuda-success)' }}>
                {cantidades[it.id] || 0} {t('gestionPedido.cajas')}
              </span>
            ) : (
              <div className="flex flex-shrink-0 items-center gap-1">
                <input
                  type="number"
                  min={0}
                  inputMode="numeric"
                  value={cantidades[it.id] ?? ''}
                  onChange={(e) => setCantidades((c) => ({ ...c, [it.id]: e.target.value }))}
                  className="w-20 rounded-lg border border-gray-200 px-2 py-1 text-right focus:border-[var(--yuda-primary)] focus:outline-none"
                  style={{ fontSize: 16 }}
                />
                <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>{t('gestionPedido.cajas')}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {sesion.notas_cliente && (
        <div className="border-t px-4 py-2.5 text-sm" style={{ borderColor: '#E0E2FA', color: 'var(--yuda-text)' }}>
          <span className="font-semibold">📝 {t('gestionPedido.notas')}:</span> {sesion.notas_cliente}
        </div>
      )}

      {pedidosGenerados.length > 0 && (
        <div className="flex flex-col gap-2 border-t px-4 py-2.5" style={{ borderColor: '#E0E2FA' }}>
          <p className="text-xs font-semibold" style={{ color: 'var(--yuda-accent)' }}>
            {t('gestionPedido.ordenesTitulo')}
          </p>
          {pedidosGenerados.map((pg) => (
            <div key={pg.id} className="flex flex-col gap-1.5 border-b pb-2 last:border-b-0 last:pb-0" style={{ borderColor: '#E0E2FA' }}>
              <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span className="flex items-center gap-1.5" style={{ color: 'var(--yuda-text)' }}>
                  <FileSpreadsheet size={14} /> {pg.supplier.replace('_', ' · ')}
                </span>
                <span
                  className="flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"
                  style={
                    pg.revisado_en_bodega_at
                      ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }
                      : { backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }
                  }
                >
                  {pg.revisado_en_bodega_at ? (
                    <>
                      <CheckCircle2 size={12} /> {t('gestionPedido.ordenRevisadaBodega')}
                    </>
                  ) : (
                    <>
                      <Clock size={12} /> {t('gestionPedido.ordenEsperandoBodega')}
                    </>
                  )}
                </span>
                {pg.revisado_en_bodega_at && pg.archivo_real_xlsx_url && (
                  <a
                    href={pg.archivo_real_xlsx_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium"
                    style={{ color: 'var(--yuda-primary)' }}
                  >
                    {t('gestionPedido.verLoQueLlego')}
                  </a>
                )}
              </div>

              {/* Fecha estimada que dio ESTE proveedor. Editable hasta que
                  bodega ya recibió la mercancía (después ya no aplica). */}
              {!pg.revisado_en_bodega_at && (
                <div className="flex flex-wrap items-center gap-2 pl-5 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {editandoFecha[pg.id] ? (
                    <>
                      <input
                        type="date"
                        value={fechaInput[pg.id] ?? ''}
                        onChange={(e) => setFechaInput((s) => ({ ...s, [pg.id]: e.target.value }))}
                        autoFocus
                        className="min-h-[32px] rounded-lg border border-gray-200 px-2"
                        style={{ fontSize: 14 }}
                      />
                      <button
                        type="button"
                        onClick={() => guardarFechaTentativa(pg)}
                        disabled={!fechaInput[pg.id] || guardandoFecha[pg.id]}
                        className="rounded-lg px-2.5 py-1 font-semibold text-white disabled:opacity-60"
                        style={{ backgroundColor: 'var(--yuda-primary)' }}
                      >
                        {t('common.guardar')}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditandoFecha((s) => ({ ...s, [pg.id]: false }))}
                      >
                        {t('common.cancelar')}
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        setFechaInput((s) => ({ ...s, [pg.id]: pg.fecha_tentativa_entrega ?? '' }))
                        setEditandoFecha((s) => ({ ...s, [pg.id]: true }))
                      }}
                      className="font-medium"
                      style={{ color: 'var(--yuda-primary)' }}
                    >
                      {pg.fecha_tentativa_entrega
                        ? t('gestionPedido.fechaTentativaValor', { fecha: pg.fecha_tentativa_entrega })
                        : t('gestionPedido.fechaTentativaSinAsignar')}
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Acciones: como el cliente ya envió sus cantidades, se puede generar directo
          el pedido al proveedor. "Enviar a confirmar" queda como paso opcional. */}
      <div className="border-t px-4 py-3" style={{ borderColor: '#E0E2FA' }}>
        <div className="flex flex-col gap-3">
          {confirmado && (
            <p className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--yuda-success-dark)' }}>
              <CheckCircle2 size={16} /> {t('gestionPedido.confirmadoOk')}
            </p>
          )}
          {porConfirmar && (
            <p className="flex items-center gap-2 text-sm" style={{ color: 'var(--yuda-warning-dark)' }}>
              <Clock size={15} /> {t('gestionPedido.esperandoConfirmacion')}
            </p>
          )}
          <p className="text-xs font-semibold" style={{ color: 'var(--yuda-accent)' }}>{t('gestionPedido.generarTitulo')}</p>
          <GenerarPedidos
            sesion_id={sesion.id}
            nombre_cliente={sesion.nombre_cliente}
            permitirCantidadesCliente
            shippingMark={sesion.shipping_mark}
          />

          {/* Una vez el cliente confirmó, avisarle a bodega es un paso aparte
              (el proveedor todavía tiene que recibir/despachar el pedido antes).
              Solo se puede una vez, y solo hacia adelante: bodega recibe esto en
              Yuda Logistic apenas se marca. */}
          {confirmado && seguimiento && (
            <div className="rounded-lg border px-3 py-2.5" style={{ borderColor: '#E0E2FA' }}>
              {seguimiento.estado === 'cotizacion_enviada' || seguimiento.estado === 'pedido_confirmado' ? (
                <button
                  type="button"
                  onClick={enviarABodega}
                  disabled={enviandoABodega}
                  className="flex items-center gap-2 self-start text-sm font-semibold disabled:opacity-60"
                  style={{ color: 'var(--yuda-primary)' }}
                >
                  <Warehouse size={16} />{' '}
                  {enviandoABodega ? t('gestionPedido.enviandoABodega') : t('gestionPedido.enviarABodega')}
                </button>
              ) : (
                <p className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--yuda-success-dark)' }}>
                  <Warehouse size={16} /> {t('gestionPedido.yaEnviadoABodega')}
                </p>
              )}
            </div>
          )}

          {/* Opcional: pedirle al cliente que confirme (útil si ajustaste cantidades) */}
          {!confirmado && (
            <button
              type="button"
              onClick={enviar}
              disabled={enviando}
              className="flex items-center gap-2 self-start text-sm font-medium disabled:opacity-60"
              style={{ color: 'var(--yuda-primary)' }}
            >
              <Send size={15} />{' '}
              {enviando
                ? t('gestionPedido.enviando')
                : porConfirmar
                  ? t('gestionPedido.reenviar')
                  : t('gestionPedido.enviarAConfirmarOpcional')}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default GestionPedidoCliente
