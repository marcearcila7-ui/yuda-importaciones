import { useEffect, useState, type ChangeEvent, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { CheckCircle2, Clock, FileSpreadsheet, Package, Pencil, Send, Upload, Warehouse } from 'lucide-react'
import { getItems } from '../api/packing'
import { enviarAConfirmar, getSeguimiento } from '../api/clientes'
import {
  actualizarFechaTentativa,
  enviarABodegaGuiado,
  getPedidos,
  listarUsuariosBodega,
  reemplazarArchivoPedidoGenerado,
  type UsuarioBodega,
} from '../api/pedidos'
import GenerarPedidos from './GenerarPedidos/GenerarPedidos'
import type { ItemResponse, Sesion } from '../types/packing'
import type { PedidoGenerado } from '../types/pedidos'
import type { Seguimiento } from '../types/seguimiento'

// Número de paso: la pantalla mezclaba muchas secciones sin indicar cuál
// seguía. Con un número al lado de cada bloque, alguien poco técnico puede
// leer de arriba a abajo y saber en cuál va, sin tener que entender de una
// todo el flujo de golpe.
function PasoNumero({ n, bloqueado }: { n: number; bloqueado?: boolean }) {
  return (
    <span
      className="flex flex-shrink-0 items-center justify-center rounded-full text-sm font-bold text-white"
      style={{ width: 26, height: 26, backgroundColor: bloqueado ? '#B7B9C7' : 'var(--yuda-primary)' }}
    >
      {n}
    </span>
  )
}

// bloqueado: además de avisar CON TEXTO que falta un paso anterior, el
// número se ve gris -para que de un vistazo, sin leer, quede claro que
// todavía no toca hacer esto.
function Paso({ n, titulo, bloqueado, children }: { n: number; titulo: string; bloqueado?: boolean; children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <PasoNumero n={n} bloqueado={bloqueado} />
      <div className="min-w-0 flex-1">
        <p className="mb-2 font-bold" style={{ color: bloqueado ? 'var(--yuda-text-secondary)' : 'var(--yuda-accent)' }}>{titulo}</p>
        {children}
      </div>
    </div>
  )
}

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
  const [usuariosBodega, setUsuariosBodega] = useState<UsuarioBodega[]>([])
  const [asignadoAId, setAsignadoAId] = useState('')
  const [reemplazandoArchivo, setReemplazandoArchivo] = useState<Record<string, boolean>>({})
  // Aunque ya esté confirmado, puede haber que corregir algo antes de generar
  // el pedido a la tienda (el cliente se equivocó, o hay que ajustar algo de
  // último momento). Sin esto, una vez confirmado quedaba de solo lectura.
  const [editandoCantidades, setEditandoCantidades] = useState(false)

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
    listarUsuariosBodega().then(setUsuariosBodega).catch(() => setUsuariosBodega([]))
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
      setEditandoCantidades(false)
      toast.success(t('gestionPedido.enviadoAConfirmar'))
      onActualizar?.()
    } catch {
      toast.error(t('gestionPedido.error'))
    } finally {
      setEnviando(false)
    }
  }

  // Le avisa a bodega que ya puede revisar este pedido: mueve el seguimiento a
  // "proveedor_recibio" (donde Yuda Logistic lo recoge), y de una vez lo
  // asigna a alguien de bodega si se eligió a quién.
  const enviarABodega = async () => {
    setEnviandoABodega(true)
    try {
      await enviarABodegaGuiado(sesion.id, asignadoAId || null)
      const actualizado = await getSeguimiento(sesion.id)
      setSeguimiento(actualizado)
      toast.success(t('gestionPedido.enviadoABodega'))
    } catch (err) {
      const mensaje = (axios.isAxiosError(err) && err.response?.data?.detail) || t('gestionPedido.errorEnviarABodega')
      toast.error(mensaje)
    } finally {
      setEnviandoABodega(false)
    }
  }

  // Si el Excel/PDF/CSV que generó el sistema para un proveedor necesita un
  // ajuste a mano, se sube acá la versión corregida en vez de la automática.
  const reemplazarArchivo = async (pg: PedidoGenerado, e: ChangeEvent<HTMLInputElement>) => {
    const archivo = e.target.files?.[0]
    e.target.value = ''
    if (!archivo) return
    setReemplazandoArchivo((s) => ({ ...s, [pg.id]: true }))
    try {
      const actualizado = await reemplazarArchivoPedidoGenerado(pg.id, archivo)
      setPedidosGenerados((lista) => lista.map((p) => (p.id === pg.id ? actualizado : p)))
      toast.success(t('gestionPedido.archivoReemplazado'))
    } catch (err) {
      const mensaje = (axios.isAxiosError(err) && err.response?.data?.detail) || t('gestionPedido.errorReemplazarArchivo')
      toast.error(mensaje)
    } finally {
      setReemplazandoArchivo((s) => ({ ...s, [pg.id]: false }))
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

      {/* Antes esto era una fila continua de secciones sin numerar: cantidades,
          notas, órdenes, botones... todo se veía como un solo bloque denso.
          Con un paso numerado por bloque, se lee de arriba a abajo sin tener
          que entender el flujo completo de una sola vez. */}
      <div className="flex flex-col gap-5 p-4">
        {/* PASO 1: qué pidió el cliente */}
        <Paso n={1} titulo={t('gestionPedido.paso1Titulo')}>
          <div className="flex flex-col divide-y rounded-lg border" style={{ borderColor: 'var(--yuda-border)' }}>
            {items.map((it) => (
              <div key={it.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <span className="min-w-0 flex-1" style={{ color: 'var(--yuda-accent)' }}>{descripcion(it)}</span>
                {confirmado && !editandoCantidades ? (
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
            <p className="mt-2 text-sm" style={{ color: 'var(--yuda-text)' }}>
              <span className="font-semibold">📝 {t('gestionPedido.notas')}:</span> {sesion.notas_cliente}
            </p>
          )}
          {/* Por si el cliente mandó mal una cantidad, o algo cambió de último
              momento: se puede corregir aunque ya esté confirmado, antes de
              generar el pedido a la tienda. */}
          {confirmado && !editandoCantidades && (
            <button
              type="button"
              onClick={() => setEditandoCantidades(true)}
              className="mt-2 flex items-center gap-2 self-start text-sm font-medium"
              style={{ color: 'var(--yuda-primary)' }}
            >
              <Pencil size={14} /> {t('gestionPedido.editarCantidades')}
            </button>
          )}
          {/* Guarda la corrección (o pide confirmación por primera vez) */}
          {(!confirmado || editandoCantidades) && (
            <div className="mt-2 flex items-center gap-3">
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
                  : editandoCantidades
                    ? t('gestionPedido.guardarCorreccion')
                    : porConfirmar
                      ? t('gestionPedido.reenviar')
                      : t('gestionPedido.enviarAConfirmarOpcional')}
              </button>
              {editandoCantidades && (
                <button
                  type="button"
                  onClick={() => setEditandoCantidades(false)}
                  className="text-sm"
                  style={{ color: 'var(--yuda-text-secondary)' }}
                >
                  {t('common.cancelar')}
                </button>
              )}
            </div>
          )}
          {porConfirmar && (
            <p className="mt-2 flex items-center gap-2 text-sm" style={{ color: 'var(--yuda-warning-dark)' }}>
              <Clock size={15} /> {t('gestionPedido.esperandoConfirmacion')}
            </p>
          )}
        </Paso>

        {/* PASO 2: generar el pedido a las tiendas (proveedores) */}
        <Paso n={2} titulo={t('gestionPedido.generarTitulo')}>
          {confirmado && (
            <p className="mb-2 flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--yuda-success-dark)' }}>
              <CheckCircle2 size={16} /> {t('gestionPedido.confirmadoOk')}
            </p>
          )}
          <GenerarPedidos
            sesion_id={sesion.id}
            nombre_cliente={sesion.nombre_cliente}
            permitirCantidadesCliente
            shippingMark={sesion.shipping_mark}
            onGenerado={() => getPedidos(sesion.id).then(setPedidosGenerados).catch(() => undefined)}
          />

          {pedidosGenerados.length > 0 && (
            <div className="mt-3 flex flex-col gap-2 rounded-lg border p-3" style={{ borderColor: 'var(--yuda-border)' }}>
              <p className="text-xs font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                {t('gestionPedido.ordenesTitulo')}
              </p>
              {pedidosGenerados.map((pg) => (
                <div key={pg.id} className="flex flex-col gap-1.5 border-b pb-2 last:border-b-0 last:pb-0" style={{ borderColor: 'var(--yuda-border)' }}>
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

                  {/* Si el archivo que generó el sistema necesita un ajuste a
                      mano, se puede reemplazar por una versión corregida antes
                      de enviarlo a bodega. */}
                  {(seguimiento?.estado === 'cotizacion_enviada' || seguimiento?.estado === 'pedido_confirmado') && (
                    <label
                      className="flex w-fit cursor-pointer items-center gap-1.5 pl-5 text-xs font-medium"
                      style={{ color: 'var(--yuda-primary)' }}
                    >
                      <Upload size={13} />{' '}
                      {reemplazandoArchivo[pg.id] ? t('common.subiendo') : t('gestionPedido.reemplazarArchivo')}
                      <input
                        type="file"
                        accept=".xlsx,.pdf,.csv"
                        className="hidden"
                        disabled={reemplazandoArchivo[pg.id]}
                        onChange={(e) => reemplazarArchivo(pg, e)}
                      />
                    </label>
                  )}

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
        </Paso>

        {/* PASO 3: avisarle a bodega. Solo aparece una vez el cliente confirmó
            (el proveedor todavía tiene que recibir/despachar el pedido antes).
            Solo se puede una vez, y solo hacia adelante: bodega recibe esto en
            Yuda Logistic apenas se marca. */}
        {confirmado && seguimiento && (
          <Paso n={3} titulo={t('gestionPedido.paso3Titulo')} bloqueado={pedidosGenerados.length === 0}>
            {seguimiento.estado === 'cotizacion_enviada' || seguimiento.estado === 'pedido_confirmado' ? (
              pedidosGenerados.length === 0 ? (
                // El backend ya rechaza avisar a bodega sin pedidos generados;
                // esto lo deja claro en la UI ANTES de que lo intente, en vez
                // de dejarla hacer clic y recibir un error después.
                <p
                  className="flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium"
                  style={{ backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }}
                >
                  <Warehouse size={16} /> {t('gestionPedido.faltaGenerarPrimero')}
                </p>
              ) : (
                <div className="flex flex-col gap-2 rounded-lg border p-3" style={{ borderColor: 'var(--yuda-border)' }}>
                  {usuariosBodega.length > 0 && (
                    <label className="flex flex-col gap-1">
                      <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                        {t('gestionPedido.asignarABodega')}
                      </span>
                      <select
                        value={asignadoAId}
                        onChange={(e) => setAsignadoAId(e.target.value)}
                        className="min-h-[40px] rounded-lg border border-gray-200 px-2 focus:border-[var(--yuda-primary)] focus:outline-none"
                        style={{ fontSize: 15 }}
                      >
                        <option value="">{t('gestionPedido.sinAsignarBodega')}</option>
                        {usuariosBodega.map((u) => (
                          <option key={u.id} value={u.id}>{u.nombre}</option>
                        ))}
                      </select>
                    </label>
                  )}
                  <button
                    type="button"
                    onClick={enviarABodega}
                    disabled={enviandoABodega}
                    className="flex min-h-[44px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: 'var(--yuda-primary)' }}
                  >
                    <Warehouse size={16} />{' '}
                    {enviandoABodega ? t('gestionPedido.enviandoABodega') : t('gestionPedido.enviarABodega')}
                  </button>
                </div>
              )
            ) : (
              <p className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--yuda-success-dark)' }}>
                <Warehouse size={16} /> {t('gestionPedido.yaEnviadoABodega')}
              </p>
            )}
          </Paso>
        )}
      </div>
    </div>
  )
}

export default GestionPedidoCliente
