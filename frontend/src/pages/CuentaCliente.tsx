import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ArrowLeft, Coins, DollarSign, HandCoins, Pencil, Plus, Trash2, Wallet } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import {
  actualizarMovimiento,
  crearMovimiento,
  eliminarMovimiento,
  getEstadoCuenta,
} from '../api/cuentas'
import { getContenedores } from '../api/contenedores'
import type { EstadoCuenta, Movimiento, MovimientoCreate } from '../types/cuenta'
import type { Contenedor } from '../types/contenedor'

type FormMov = {
  contenedor_id: string
  envio: string
  fecha: string
  guia: string
  descripcion: string
  valor_mercancia: string
  comision_yuda: string
  abono: string
  nota: string
}

const FORM_VACIO: FormMov = {
  contenedor_id: '', envio: '', fecha: '', guia: '', descripcion: '',
  valor_mercancia: '', comision_yuda: '', abono: '', nota: '',
}

function CuentaCliente() {
  const { clienteId = '' } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [cuenta, setCuenta] = useState<EstadoCuenta | null>(null)
  const [contenedores, setContenedores] = useState<Contenedor[]>([])
  const [cargando, setCargando] = useState(true)
  const [form, setForm] = useState<FormMov>(FORM_VACIO)
  const [editandoId, setEditandoId] = useState<string | null>(null)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [guardando, setGuardando] = useState(false)

  useEffect(() => {
    let activo = true
    ;(async () => {
      setCargando(true)
      try {
        const [c, conts] = await Promise.all([
          getEstadoCuenta(clienteId),
          getContenedores().catch(() => [] as Contenedor[]),
        ])
        if (!activo) return
        setCuenta(c)
        setContenedores(conts)
      } catch {
        if (activo) toast.error(t('cuenta.errorCargar'))
      } finally {
        if (activo) setCargando(false)
      }
    })()
    return () => { activo = false }
  }, [clienteId, t])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const setCampo = (k: keyof FormMov, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const abrirNuevo = () => {
    setForm(FORM_VACIO)
    setEditandoId(null)
    setMostrarForm(true)
  }

  const abrirEdicion = (m: Movimiento) => {
    setForm({
      contenedor_id: m.contenedor_id ?? '',
      envio: m.envio ?? '',
      fecha: m.fecha ?? '',
      guia: m.guia ?? '',
      descripcion: m.descripcion ?? '',
      valor_mercancia: String(m.valor_mercancia ?? ''),
      comision_yuda: String(m.comision_yuda ?? ''),
      abono: String(m.abono ?? ''),
      nota: m.nota ?? '',
    })
    setEditandoId(m.id)
    setMostrarForm(true)
  }

  const guardar = async () => {
    setGuardando(true)
    try {
      const payload: MovimientoCreate = {
        contenedor_id: form.contenedor_id || null,
        envio: form.envio.trim() || null,
        fecha: form.fecha || null,
        guia: form.guia.trim() || null,
        descripcion: form.descripcion.trim() || null,
        valor_mercancia: Number(form.valor_mercancia) || 0,
        // Vacío → el backend calcula la comisión (5%).
        comision_yuda: form.comision_yuda === '' ? null : Number(form.comision_yuda),
        abono: Number(form.abono) || 0,
        nota: form.nota.trim() || null,
      }
      const actualizada = editandoId
        ? await actualizarMovimiento(clienteId, editandoId, payload)
        : await crearMovimiento(clienteId, payload)
      setCuenta(actualizada)
      setMostrarForm(false)
      setForm(FORM_VACIO)
      setEditandoId(null)
    } catch {
      toast.error(t('cuenta.errorGuardar'))
    } finally {
      setGuardando(false)
    }
  }

  const borrar = async (m: Movimiento) => {
    if (!window.confirm(t('cuenta.confirmarEliminar'))) return
    try {
      const actualizada = await eliminarMovimiento(clienteId, m.id)
      setCuenta(actualizada)
    } catch {
      toast.error(t('cuenta.errorGuardar'))
    }
  }

  const codigoContenedor = useMemo(() => {
    const map: Record<string, string> = {}
    contenedores.forEach((c) => { map[c.id] = c.codigo })
    return map
  }, [contenedores])

  if (cargando) return <div className="p-6" style={{ color: 'var(--yuda-text-secondary)' }}>{t('detalle.cargando')}</div>
  if (!cuenta) return <div className="p-6">{t('cuenta.errorCargar')}</div>

  return (
    <div className="flex flex-col gap-5 p-4 sm:p-6">
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="flex w-fit items-center gap-1 text-sm font-medium"
        style={{ color: 'var(--yuda-text-secondary)' }}
      >
        <ArrowLeft size={16} /> {t('cuenta.volver')}
      </button>

      <div>
        <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>{cuenta.nombre}</h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('cuenta.titulo')}
          {cuenta.nit ? ` · ${t('cuenta.nit')}: ${cuenta.nit}` : ''}
          {cuenta.empresa ? ` · ${cuenta.empresa}` : ''}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <MetricCard titulo={t('cuenta.compras')} valor={`$ ${fmt(cuenta.compras_totales)}`} icono={<DollarSign size={20} />} color="var(--yuda-primary)" />
        <MetricCard titulo={t('cuenta.comision')} valor={`$ ${fmt(cuenta.comision_total)}`} icono={<Coins size={20} />} color="var(--yuda-warning)" />
        <MetricCard titulo={t('cuenta.abonos')} valor={`$ ${fmt(cuenta.abonos_totales)}`} icono={<HandCoins size={20} />} color="var(--yuda-success)" />
        <MetricCard titulo={t('cuenta.saldoPendiente')} valor={`$ ${fmt(cuenta.saldo_pendiente)}`} icono={<Wallet size={20} />} color="var(--yuda-accent)" />
      </div>

      <section className="card flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('cuenta.movimientos')}</h2>
          {!mostrarForm && (
            <button
              type="button"
              onClick={abrirNuevo}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: 'var(--yuda-primary)' }}
            >
              <Plus size={16} /> {t('cuenta.nuevo')}
            </button>
          )}
        </div>

        {mostrarForm && (
          <div className="rounded-lg border p-3" style={{ borderColor: 'var(--yuda-border)', background: 'var(--yuda-bg)' }}>
            <h3 className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-text)' }}>
              {editandoId ? t('cuenta.editar') : t('cuenta.nuevo')}
            </h3>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              <label className="flex flex-col gap-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('cuenta.contenedor')}
                <select value={form.contenedor_id} onChange={(e) => setCampo('contenedor_id', e.target.value)} className="rounded-lg border px-2 py-1.5 text-sm" style={{ borderColor: 'var(--yuda-border)' }}>
                  <option value="">{t('cuenta.sinContenedor')}</option>
                  {contenedores.map((c) => <option key={c.id} value={c.id}>{c.codigo}</option>)}
                </select>
              </label>
              <Campo label={t('cuenta.envio')} value={form.envio} onChange={(v) => setCampo('envio', v)} />
              <Campo label={t('cuenta.fecha')} type="date" value={form.fecha} onChange={(v) => setCampo('fecha', v)} />
              <Campo label={t('cuenta.guia')} value={form.guia} onChange={(v) => setCampo('guia', v)} />
              <Campo label={t('cuenta.descripcion')} value={form.descripcion} onChange={(v) => setCampo('descripcion', v)} />
              <Campo label={t('cuenta.valor')} type="number" value={form.valor_mercancia} onChange={(v) => setCampo('valor_mercancia', v)} />
              <Campo label={t('cuenta.comisionCol')} type="number" value={form.comision_yuda} onChange={(v) => setCampo('comision_yuda', v)} hint={t('cuenta.comisionAuto')} />
              <Campo label={t('cuenta.abono')} type="number" value={form.abono} onChange={(v) => setCampo('abono', v)} />
              <Campo label={t('cuenta.nota')} value={form.nota} onChange={(v) => setCampo('nota', v)} />
            </div>
            <div className="mt-3 flex gap-2">
              <button type="button" onClick={guardar} disabled={guardando} className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" style={{ backgroundColor: 'var(--yuda-success)' }}>
                {t('cuenta.guardar')}
              </button>
              <button type="button" onClick={() => { setMostrarForm(false); setEditandoId(null) }} className="rounded-lg border px-4 py-2 text-sm font-medium" style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-secondary)' }}>
                {t('cuenta.cancelar')}
              </button>
            </div>
          </div>
        )}

        {cuenta.movimientos.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cuenta.sinMovimientos')}</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}>
                  <th className="px-3 py-2 text-left font-semibold">{t('cuenta.envio')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('cuenta.fecha')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('cuenta.guia')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('cuenta.descripcion')}</th>
                  <th className="px-3 py-2 text-left font-semibold">{t('cuenta.contenedor')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('cuenta.valor')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('cuenta.comisionCol')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('cuenta.abono')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('cuenta.saldo')}</th>
                  <th className="px-3 py-2 text-right font-semibold">{t('cuenta.acciones')}</th>
                </tr>
              </thead>
              <tbody>
                {cuenta.movimientos.map((m, i) => (
                  <tr key={m.id} style={{ background: i % 2 ? 'var(--yuda-bg)' : 'transparent', borderBottom: '1px solid var(--yuda-border)' }}>
                    <td className="px-3 py-2">{m.envio ?? ''}</td>
                    <td className="px-3 py-2">{m.fecha ?? ''}</td>
                    <td className="px-3 py-2">{m.guia ?? ''}</td>
                    <td className="px-3 py-2">{m.descripcion ?? ''}</td>
                    <td className="px-3 py-2">{m.contenedor_id ? codigoContenedor[m.contenedor_id] ?? '' : ''}</td>
                    <td className="px-3 py-2 text-right">{fmt(m.valor_mercancia)}</td>
                    <td className="px-3 py-2 text-right">{fmt(m.comision_yuda)}</td>
                    <td className="px-3 py-2 text-right">{fmt(m.abono)}</td>
                    <td className="px-3 py-2 text-right font-semibold">{fmt(m.saldo)}</td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-2">
                        <button type="button" onClick={() => abrirEdicion(m)} aria-label={t('cuenta.editar')} style={{ color: 'var(--yuda-primary)' }}><Pencil size={16} /></button>
                        <button type="button" onClick={() => borrar(m)} aria-label={t('cuenta.eliminar')} style={{ color: 'var(--yuda-error)' }}><Trash2 size={16} /></button>
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

export default CuentaCliente
