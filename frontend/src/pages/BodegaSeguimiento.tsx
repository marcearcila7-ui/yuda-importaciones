import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { CheckCircle2, ClipboardList, Package, Truck, UserCircle2, Warehouse } from 'lucide-react'
import {
  asignarPedidoBodega,
  getBodegaResumen,
  listarUsuariosBodega,
  type UsuarioBodega,
} from '../api/pedidos'
import type { PedidoBodegaSeguimiento } from '../types/pedidos'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

const BADGE_ESTADO: Record<string, { bg: string; fg: string; icon: React.ReactNode }> = {
  proveedor_recibio: { bg: 'var(--yuda-warning-soft)', fg: 'var(--yuda-warning-dark)', icon: <Package size={13} /> },
  en_bodega: { bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)', icon: <Warehouse size={13} /> },
  en_transito: { bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)', icon: <Truck size={13} /> },
  en_destino: { bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)', icon: <Truck size={13} /> },
  entregado: { bg: 'var(--yuda-success-soft)', fg: 'var(--yuda-success-dark)', icon: <CheckCircle2 size={13} /> },
}

// Estados de envío, en el mismo orden en que aparecen en el timeline, para
// que el selector de filtro se lea de arriba a abajo como el flujo real.
const ORDEN_ESTADOS = ['proveedor_recibio', 'en_bodega', 'en_transito', 'en_destino', 'entregado']

function BodegaSeguimiento() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [pedidos, setPedidos] = useState<PedidoBodegaSeguimiento[]>([])
  const [usuariosBodega, setUsuariosBodega] = useState<UsuarioBodega[]>([])
  const [cargando, setCargando] = useState(true)
  const [reasignando, setReasignando] = useState<Record<string, boolean>>({})
  const [busqueda, setBusqueda] = useState('')
  const [filtroEstado, setFiltroEstado] = useState('')
  const [filtroAsignado, setFiltroAsignado] = useState('')

  useEffect(() => {
    setCargando(true)
    Promise.all([getBodegaResumen(), listarUsuariosBodega()])
      .then(([p, u]) => {
        setPedidos(p)
        setUsuariosBodega(u)
      })
      .catch(() => toast.error(t('bodegaSeguimiento.errorCargar')))
      .finally(() => setCargando(false))
  }, [t])

  const reasignar = async (sesionId: string, asignadoAId: string) => {
    setReasignando((s) => ({ ...s, [sesionId]: true }))
    try {
      const r = await asignarPedidoBodega(sesionId, asignadoAId || null)
      setPedidos((lista) =>
        lista.map((p) =>
          p.sesion_id === sesionId
            ? { ...p, bodega_asignado_a_id: r.bodega_asignado_a_id, bodega_asignado_a_nombre: r.bodega_asignado_a_nombre }
            : p,
        ),
      )
      toast.success(t('bodegaSeguimiento.reasignado'))
    } catch (err) {
      const mensaje = (axios.isAxiosError(err) && err.response?.data?.detail) || t('bodegaSeguimiento.errorReasignar')
      toast.error(mensaje)
    } finally {
      setReasignando((s) => ({ ...s, [sesionId]: false }))
    }
  }

  const locale = LOCALES[i18n.language] || 'es-ES'
  const fmtFecha = (iso: string) =>
    new Date(iso).toLocaleString(locale, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })

  const texto = busqueda.trim().toLowerCase()
  const pedidosFiltrados = pedidos.filter((p) => {
    if (texto && !p.cliente_nombre.toLowerCase().includes(texto) && !p.numero.toLowerCase().includes(texto)) {
      return false
    }
    if (filtroEstado && p.estado_envio !== filtroEstado) return false
    if (filtroAsignado === 'sin_asignar' && p.bodega_asignado_a_id) return false
    if (filtroAsignado && filtroAsignado !== 'sin_asignar' && p.bodega_asignado_a_id !== filtroAsignado) return false
    return true
  })

  return (
    <div>
      <h1 className="mb-1" style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>
        {t('bodegaSeguimiento.titulo')}
      </h1>
      <p className="mb-5 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
        {t('bodegaSeguimiento.ayuda')}
      </p>

      {!cargando && pedidos.length > 0 && (
        <div className="card mb-5 flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('bodegaSeguimiento.buscarLabel')}
            <input
              type="text"
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder={t('bodegaSeguimiento.buscarPlaceholder')}
              className="rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none"
              style={{ fontSize: 16 }}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('bodegaSeguimiento.filtroEstadoLabel')}
            <select
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
              className="min-h-[44px] rounded-lg border border-gray-200 px-3 focus:border-[var(--yuda-primary)] focus:outline-none"
              style={{ fontSize: 16 }}
            >
              <option value="">{t('bodegaSeguimiento.filtroTodos')}</option>
              {ORDEN_ESTADOS.map((estado) => (
                <option key={estado} value={estado}>{t(`bodegaSeguimiento.estado.${estado}`)}</option>
              ))}
            </select>
          </label>
          {usuariosBodega.length > 0 && (
            <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('bodegaSeguimiento.filtroAsignadoLabel')}
              <select
                value={filtroAsignado}
                onChange={(e) => setFiltroAsignado(e.target.value)}
                className="min-h-[44px] rounded-lg border border-gray-200 px-3 focus:border-[var(--yuda-primary)] focus:outline-none"
                style={{ fontSize: 16 }}
              >
                <option value="">{t('bodegaSeguimiento.filtroTodos')}</option>
                <option value="sin_asignar">{t('bodegaSeguimiento.sinAsignar')}</option>
                {usuariosBodega.map((u) => (
                  <option key={u.id} value={u.id}>{u.nombre}</option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}

      {cargando ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('common.cargando')}
        </p>
      ) : pedidos.length === 0 ? (
        <div className="rounded-xl border p-4" style={{ borderColor: 'var(--yuda-border)' }}>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('bodegaSeguimiento.sinPedidos')}
          </p>
        </div>
      ) : pedidosFiltrados.length === 0 ? (
        <div className="rounded-xl border p-4" style={{ borderColor: 'var(--yuda-border)' }}>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('bodegaSeguimiento.sinResultados')}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {pedidosFiltrados.map((p) => {
            const badge = BADGE_ESTADO[p.estado_envio] ?? BADGE_ESTADO.proveedor_recibio
            return (
              <div key={p.sesion_id} className="rounded-xl border p-4" style={{ borderColor: 'var(--yuda-border)' }}>
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => navigate(`/cotizacion/${p.sesion_id}`)}
                    className="text-left"
                  >
                    <p className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>{p.cliente_nombre}</p>
                    <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {p.numero} · {new Date(p.fecha).toLocaleDateString(locale)}
                    </p>
                  </button>
                  <span
                    className="flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"
                    style={{ backgroundColor: badge.bg, color: badge.fg }}
                  >
                    {badge.icon} {t(`bodegaSeguimiento.estado.${p.estado_envio}`)}
                  </span>
                </div>

                {p.total_ordenes > 0 && (
                  <p className="mb-2 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {t('bodegaSeguimiento.ordenesRevisadas', { n: p.ordenes_revisadas, total: p.total_ordenes })}
                  </p>
                )}

                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span
                    className="flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium"
                    style={{ backgroundColor: 'var(--yuda-bg)', color: 'var(--yuda-text)' }}
                  >
                    <UserCircle2 size={14} />{' '}
                    {p.bodega_asignado_a_nombre
                      ? t('bodegaSeguimiento.asignadoA', { nombre: p.bodega_asignado_a_nombre })
                      : t('bodegaSeguimiento.sinAsignar')}
                  </span>
                  {usuariosBodega.length > 0 && (
                    <select
                      disabled={reasignando[p.sesion_id]}
                      value=""
                      onChange={(e) => e.target.value && reasignar(p.sesion_id, e.target.value)}
                      className="min-h-[32px] rounded-lg border px-2 text-xs focus:outline-none"
                      style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-secondary)' }}
                    >
                      <option value="">{t('bodegaSeguimiento.reasignarA')}</option>
                      {usuariosBodega
                        .filter((u) => u.id !== p.bodega_asignado_a_id)
                        .map((u) => (
                          <option key={u.id} value={u.id}>{u.nombre}</option>
                        ))}
                    </select>
                  )}
                </div>

                {p.actividad_reciente.length > 0 && (
                  <details>
                    <summary
                      className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold"
                      style={{ color: 'var(--yuda-text-secondary)' }}
                    >
                      <ClipboardList size={13} /> {t('bodegaSeguimiento.verActividad', { n: p.actividad_reciente.length })}
                    </summary>
                    <div className="mt-2 flex flex-col gap-1.5">
                      {p.actividad_reciente.map((a, i) => (
                        <div key={i} className="rounded-lg px-2.5 py-1.5 text-xs" style={{ backgroundColor: 'var(--yuda-bg)' }}>
                          <p style={{ color: 'var(--yuda-text)' }}>{a.detalle || t(`bodegaSeguimiento.tipoActividad.${a.tipo}`)}</p>
                          <p style={{ color: 'var(--yuda-text-secondary)' }}>
                            {a.usuario_nombre || '—'} · {fmtFecha(a.created_at)}
                          </p>
                        </div>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default BodegaSeguimiento
