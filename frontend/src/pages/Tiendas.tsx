import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, Coins, Pencil, Plus, Store, Trash2, Wallet } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import {
  actualizarPedidoTienda,
  crearPedidoTienda,
  eliminarPedidoTienda,
  getEmpleadas,
  getPedidosTienda,
} from '../api/tiendas'
import type { EmpleadaResumen, PedidoTienda, PedidoTiendaCreate } from '../types/tienda'

type FormT = {
  nombre_tienda: string
  fecha_pedido: string
  monto_total: string
  pct_comision_tienda: string
  empleada_id: string
  fecha_pago_30: string
  fecha_estimada_entrega: string
  fecha_real_entrega: string
  fecha_estimada_pago_70: string
  fecha_pago_70: string
  notas: string
}

const VACIO: FormT = {
  nombre_tienda: '', fecha_pedido: '', monto_total: '', pct_comision_tienda: '', empleada_id: '',
  fecha_pago_30: '', fecha_estimada_entrega: '', fecha_real_entrega: '',
  fecha_estimada_pago_70: '', fecha_pago_70: '', notas: '',
}

function Tiendas() {
  const { t } = useTranslation()
  const [pedidos, setPedidos] = useState<PedidoTienda[] | null>(null)
  const [empleadas, setEmpleadas] = useState<EmpleadaResumen[]>([])
  const [form, setForm] = useState<FormT>(VACIO)
  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [guardando, setGuardando] = useState(false)

  const cargar = () => getPedidosTienda().then(setPedidos).catch(() => setPedidos([]))
  useEffect(() => {
    cargar()
    getEmpleadas().then(setEmpleadas).catch(() => setEmpleadas([]))
  }, [])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const setCampo = (k: keyof FormT, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const totales = useMemo(() => {
    const list = pedidos ?? []
    const saldo70 = list.filter((p) => !p.fecha_pago_70).reduce((a, p) => a + p.monto_70, 0)
    const comision = list.reduce((a, p) => a + p.monto_comision, 0)
    const alertas = list.filter((p) => p.alerta_pago_70).length
    return { saldo70, comision, alertas, total: list.length }
  }, [pedidos])

  const abrirNuevo = () => { setForm(VACIO); setEditandoId(null); setMostrarForm(true) }
  const abrirEdicion = (p: PedidoTienda) => {
    setForm({
      nombre_tienda: p.nombre_tienda, fecha_pedido: p.fecha_pedido ?? '',
      monto_total: String(p.monto_total ?? ''), pct_comision_tienda: String(p.pct_comision_tienda ?? ''),
      empleada_id: p.empleada_id ?? '', fecha_pago_30: p.fecha_pago_30 ?? '',
      fecha_estimada_entrega: p.fecha_estimada_entrega ?? '', fecha_real_entrega: p.fecha_real_entrega ?? '',
      fecha_estimada_pago_70: p.fecha_estimada_pago_70 ?? '', fecha_pago_70: p.fecha_pago_70 ?? '',
      notas: p.notas ?? '',
    })
    setEditandoId(p.id); setMostrarForm(true)
  }

  const guardar = async () => {
    if (!form.nombre_tienda.trim()) { toast.error(t('tiendas.faltaNombre')); return }
    setGuardando(true)
    try {
      const payload: PedidoTiendaCreate = {
        nombre_tienda: form.nombre_tienda.trim(),
        fecha_pedido: form.fecha_pedido || null,
        monto_total: Number(form.monto_total) || 0,
        pct_comision_tienda: Number(form.pct_comision_tienda) || 0,
        empleada_id: form.empleada_id || null,
        fecha_pago_30: form.fecha_pago_30 || null,
        fecha_estimada_entrega: form.fecha_estimada_entrega || null,
        fecha_real_entrega: form.fecha_real_entrega || null,
        fecha_estimada_pago_70: form.fecha_estimada_pago_70 || null,
        fecha_pago_70: form.fecha_pago_70 || null,
        notas: form.notas.trim() || null,
      }
      if (editandoId) await actualizarPedidoTienda(editandoId, payload)
      else await crearPedidoTienda(payload)
      setMostrarForm(false); setForm(VACIO); setEditandoId(null)
      await cargar()
    } catch {
      toast.error(t('tiendas.errorGuardar'))
    } finally {
      setGuardando(false)
    }
  }

  const borrar = async (p: PedidoTienda) => {
    if (!window.confirm(t('tiendas.confirmarEliminar', { tienda: p.nombre_tienda }))) return
    try { await eliminarPedidoTienda(p.id); await cargar() } catch { toast.error(t('tiendas.errorGuardar')) }
  }

  const chipEstado = (e: string) =>
    e === 'pagado' ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
    : e === 'parcial' ? { backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }
    : { backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }

  return (
    <div className="flex flex-col gap-5 p-4 sm:p-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }} className="flex items-center gap-2">
          <Store size={22} /> {t('tiendas.titulo')}
        </h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('tiendas.subtitulo')}</p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <MetricCard titulo={t('tiendas.mPedidos')} valor={totales.total} icono={<Store size={20} />} color="var(--yuda-primary)" />
        <MetricCard titulo={t('tiendas.mSaldo70')} valor={`¥ ${fmt(totales.saldo70)}`} icono={<Wallet size={20} />} color="var(--yuda-accent)" />
        <MetricCard titulo={t('tiendas.mComision')} valor={`¥ ${fmt(totales.comision)}`} icono={<Coins size={20} />} color="var(--yuda-warning)" />
        <MetricCard titulo={t('tiendas.mAlertas')} valor={totales.alertas} icono={<AlertTriangle size={20} />} color="var(--yuda-error)" />
      </div>

      <section className="card flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('tiendas.pedidos')}</h2>
          {!mostrarForm && (
            <button type="button" onClick={abrirNuevo} className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-white" style={{ backgroundColor: 'var(--yuda-primary)' }}>
              <Plus size={16} /> {t('tiendas.nuevo')}
            </button>
          )}
        </div>

        {mostrarForm && (
          <div className="rounded-lg border p-3" style={{ borderColor: 'var(--yuda-border)', background: 'var(--yuda-bg)' }}>
            <h3 className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-text)' }}>
              {editandoId ? t('tiendas.editar') : t('tiendas.nuevo')}
            </h3>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <Campo label={t('tiendas.nombre')} value={form.nombre_tienda} onChange={(v) => setCampo('nombre_tienda', v)} />
              <Campo label={t('tiendas.fechaPedido')} type="date" value={form.fecha_pedido} onChange={(v) => setCampo('fecha_pedido', v)} />
              <Campo label={t('tiendas.montoTotal')} type="number" value={form.monto_total} onChange={(v) => setCampo('monto_total', v)} />
              <Campo label={t('tiendas.pctComision')} type="number" value={form.pct_comision_tienda} onChange={(v) => setCampo('pct_comision_tienda', v)} />
              <label className="flex flex-col gap-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('tiendas.empleada')}
                <select value={form.empleada_id} onChange={(e) => setCampo('empleada_id', e.target.value)} className="rounded-lg border px-2 py-1.5 text-sm" style={{ borderColor: 'var(--yuda-border)' }}>
                  <option value="">—</option>
                  {empleadas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
              </label>
              <Campo label={t('tiendas.fechaPago30')} type="date" value={form.fecha_pago_30} onChange={(v) => setCampo('fecha_pago_30', v)} />
              <Campo label={t('tiendas.fechaEstEntrega')} type="date" value={form.fecha_estimada_entrega} onChange={(v) => setCampo('fecha_estimada_entrega', v)} />
              <Campo label={t('tiendas.fechaRealEntrega')} type="date" value={form.fecha_real_entrega} onChange={(v) => setCampo('fecha_real_entrega', v)} />
              <Campo label={t('tiendas.fechaEstPago70')} type="date" value={form.fecha_estimada_pago_70} onChange={(v) => setCampo('fecha_estimada_pago_70', v)} hint={t('tiendas.hintPago70')} />
              <Campo label={t('tiendas.fechaPago70')} type="date" value={form.fecha_pago_70} onChange={(v) => setCampo('fecha_pago_70', v)} />
              <Campo label={t('tiendas.notas')} value={form.notas} onChange={(v) => setCampo('notas', v)} />
            </div>
            <div className="mt-3 flex gap-2">
              <button type="button" onClick={guardar} disabled={guardando} className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" style={{ backgroundColor: 'var(--yuda-success)' }}>
                {t('tiendas.guardar')}
              </button>
              <button type="button" onClick={() => { setMostrarForm(false); setEditandoId(null) }} className="rounded-lg border px-4 py-2 text-sm font-medium" style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-secondary)' }}>
                {t('tiendas.cancelar')}
              </button>
            </div>
          </div>
        )}

        {pedidos && pedidos.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('tiendas.sinPedidos')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}>
                  <th className="px-3 py-2 text-left font-semibold">{t('tiendas.nombre')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('tiendas.montoTotal')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('tiendas.c30')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('tiendas.c70')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('tiendas.comision')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('tiendas.pago70')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('tiendas.empleada')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('tiendas.estado')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('tiendas.acciones')}</th>
                </tr>
              </thead>
              <tbody>
                {(pedidos ?? []).map((p, i) => (
                  <tr key={p.id} style={{ background: p.alerta_pago_70 ? 'var(--yuda-error-soft)' : i % 2 ? 'var(--yuda-bg)' : 'transparent', borderBottom: '1px solid var(--yuda-border)' }}>
                    <td className="px-3 py-2 font-medium">{p.nombre_tienda}</td>
                    <td className="px-3 py-2 text-right">{fmt(p.monto_total)}</td>
                    <td className="px-3 py-2 text-right">{fmt(p.monto_30)}</td>
                    <td className="px-3 py-2 text-right">{fmt(p.monto_70)}</td>
                    <td className="px-3 py-2 text-right">{fmt(p.monto_comision)}</td>
                    <td className="px-3 py-2">
                      {p.fecha_pago_70
                        ? p.fecha_pago_70
                        : p.fecha_estimada_pago_70
                          ? (
                            <span className="flex items-center gap-1" style={{ color: p.alerta_pago_70 ? 'var(--yuda-error)' : 'var(--yuda-text-secondary)' }}>
                              {p.alerta_pago_70 && <AlertTriangle size={13} />}
                              {p.fecha_estimada_pago_70}
                              {p.dias_para_pago_70 !== null && p.alerta_pago_70 && (
                                <span className="text-xs">({p.dias_para_pago_70 < 0 ? t('tiendas.vencido') : t('tiendas.enDias', { d: p.dias_para_pago_70 })})</span>
                              )}
                            </span>
                          )
                          : '—'}
                    </td>
                    <td className="px-3 py-2">{p.empleada_nombre ?? '—'}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chipEstado(p.estado)}>{t(`tiendas.estado_${p.estado}`)}</span>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-2">
                        <button type="button" onClick={() => abrirEdicion(p)} aria-label={t('tiendas.editar')} style={{ color: 'var(--yuda-primary)' }}><Pencil size={16} /></button>
                        <button type="button" onClick={() => borrar(p)} aria-label={t('tiendas.eliminar')} style={{ color: 'var(--yuda-error)' }}><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function Campo({ label, value, onChange, type = 'text', hint }: {
  label: string; value: string; onChange: (v: string) => void; type?: string; hint?: string
}) {
  return (
    <label className="flex flex-col gap-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
      {label}
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} className="rounded-lg border px-2 py-1.5 text-sm" style={{ borderColor: 'var(--yuda-border)' }} />
      {hint ? <span style={{ fontSize: 10 }}>{hint}</span> : null}
    </label>
  )
}

export default Tiendas
