import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ArrowLeft, Download, FileText, Package, Pencil, Plus, Trash2, Wallet } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import {
  actualizarMovimiento,
  crearMovimiento,
  eliminarMovimiento,
  exportarCuentaExcel,
  exportarCuentaPDF,
  getEstadoCuenta,
} from '../api/cuentas'
import { getContenedores } from '../api/contenedores'
import { getCotizacionesCliente } from '../api/clientes'
import { MONEDAS, MONEDAS_ORIGEN } from '../types/cuenta'
import type { EstadoCuenta, Movimiento, MovimientoCreate, PedidoCuenta } from '../types/cuenta'
import type { Contenedor } from '../types/contenedor'
import type { Sesion } from '../types/packing'

type FormMov = {
  sesion_id: string
  moneda: string
  contenedor_id: string
  envio: string
  fecha: string
  guia: string
  descripcion: string
  valor_mercancia: string
  comision_yuda: string
  abono: string
  // De donde salio el abono: se guarda como entro y a que tasa
  monto_origen: string
  moneda_origen: string
  tasa_cambio: string
  nota: string
}

const FORM_VACIO: FormMov = {
  sesion_id: '', moneda: 'USD', contenedor_id: '', envio: '', fecha: '', guia: '', descripcion: '',
  valor_mercancia: '', comision_yuda: '', abono: '',
  monto_origen: '', moneda_origen: 'USDT', tasa_cambio: '', nota: '',
}

// Mismo formato de número que el backend (YUDA-AAAAMMDD-ID6).
function numeroPedido(s: Sesion): string {
  return `YUDA-${(s.fecha || '').replace(/-/g, '')}-${s.id.slice(0, 6).toUpperCase()}`
}

function CuentaCliente() {
  const { clienteId = '' } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [cuenta, setCuenta] = useState<EstadoCuenta | null>(null)
  const [contenedores, setContenedores] = useState<Contenedor[]>([])
  const [cotizaciones, setCotizaciones] = useState<Sesion[]>([])
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
        const [c, conts, cots] = await Promise.all([
          getEstadoCuenta(clienteId),
          getContenedores().catch(() => [] as Contenedor[]),
          getCotizacionesCliente(clienteId).catch(() => [] as Sesion[]),
        ])
        if (!activo) return
        setCuenta(c)
        setContenedores(conts)
        setCotizaciones(cots)
      } catch {
        if (activo) toast.error(t('cuenta.errorCargar'))
      } finally {
        if (activo) setCargando(false)
      }
    })()
    return () => { activo = false }
  }, [clienteId, t])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const fmtMon = (n: number, moneda: string) => `${moneda} ${fmt(n)}`
  const setCampo = (k: keyof FormMov, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const [descargando, setDescargando] = useState<'excel' | 'pdf' | null>(null)

  const descargar = async (tipo: 'excel' | 'pdf') => {
    if (!clienteId) return
    setDescargando(tipo)
    try {
      const blob = tipo === 'excel'
        ? await exportarCuentaExcel(clienteId)
        : await exportarCuentaPDF(clienteId)
      const url = URL.createObjectURL(blob)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `Cuenta_${cuenta?.nombre ?? ''}.${tipo === 'excel' ? 'xlsx' : 'pdf'}`
      enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      toast.error(t('cuenta.errorDescargar'))
    } finally {
      setDescargando(null)
    }
  }

  // El abono en la moneda de la cuenta sale de lo que entro por la tasa. Se
  // muestra calculado para que la contadora vea el resultado antes de guardar y
  // no tenga que hacer la cuenta aparte, que es donde se cuelan los errores.
  const abonoCalculado =
    form.monto_origen !== '' && form.tasa_cambio !== ''
      ? Math.round(Number(form.monto_origen) * Number(form.tasa_cambio) * 100) / 100
      : null

  // Moneda ya fijada de un pedido (por sus movimientos), o null si aún no tiene.
  const monedaDelPedido = (sesionId: string): string | null => {
    if (!sesionId || !cuenta) return null
    const p = cuenta.pedidos.find((x) => x.sesion_id === sesionId)
    return p && p.movimientos.length > 0 ? p.moneda : null
  }

  const abrirNuevo = (sesionId = '') => {
    setForm({ ...FORM_VACIO, sesion_id: sesionId, moneda: monedaDelPedido(sesionId) ?? 'USD' })
    setEditandoId(null)
    setMostrarForm(true)
  }

  // Al cambiar el pedido en el form, si ese pedido ya tiene moneda, se adopta.
  const cambiarPedido = (sesionId: string) => {
    setForm((f) => ({ ...f, sesion_id: sesionId, moneda: monedaDelPedido(sesionId) ?? f.moneda }))
  }

  const abrirEdicion = (m: Movimiento) => {
    setForm({
      sesion_id: m.sesion_id ?? '',
      moneda: m.moneda ?? 'USD',
      contenedor_id: m.contenedor_id ?? '',
      envio: m.envio ?? '',
      fecha: m.fecha ?? '',
      guia: m.guia ?? '',
      descripcion: m.descripcion ?? '',
      valor_mercancia: String(m.valor_mercancia ?? ''),
      comision_yuda: String(m.comision_yuda ?? ''),
      abono: String(m.abono ?? ''),
      monto_origen: m.monto_origen != null ? String(m.monto_origen) : '',
      moneda_origen: m.moneda_origen || 'USDT',
      tasa_cambio: m.tasa_cambio != null ? String(m.tasa_cambio) : '',
      nota: m.nota ?? '',
    })
    setEditandoId(m.id)
    setMostrarForm(true)
  }

  const guardar = async () => {
    setGuardando(true)
    try {
      const payload: MovimientoCreate = {
        sesion_id: form.sesion_id || null,
        moneda: form.moneda || 'USD',
        contenedor_id: form.contenedor_id || null,
        envio: form.envio.trim() || null,
        fecha: form.fecha || null,
        guia: form.guia.trim() || null,
        descripcion: form.descripcion.trim() || null,
        valor_mercancia: Number(form.valor_mercancia) || 0,
        // Vacío → el backend calcula la comisión (5%).
        comision_yuda: form.comision_yuda === '' ? null : Number(form.comision_yuda),
        abono: Number(form.abono) || 0,
        monto_origen: form.monto_origen === '' ? null : Number(form.monto_origen),
        moneda_origen: form.monto_origen === '' ? null : form.moneda_origen,
        tasa_cambio: form.tasa_cambio === '' ? null : Number(form.tasa_cambio),
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

  const tituloPedido = (p: PedidoCuenta) =>
    p.sesion_id ? (p.pedido_numero ?? p.sesion_id.slice(0, 6).toUpperCase()) : t('cuenta.sinPedido')

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

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>{cuenta.nombre}</h1>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('cuenta.titulo')}
            {cuenta.nit ? ` · ${t('cuenta.nit')}: ${cuenta.nit}` : ''}
            {cuenta.empresa ? ` · ${cuenta.empresa}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* El estado de cuenta como documento: es lo que se le manda al cliente */}
          <button
            type="button"
            onClick={() => descargar('excel')}
            disabled={descargando !== null}
            className="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-60"
            style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-success)' }}
          >
            <Download size={16} />
            {descargando === 'excel' ? t('cuenta.descargando') : t('cuenta.descargarExcel')}
          </button>
          <button
            type="button"
            onClick={() => descargar('pdf')}
            disabled={descargando !== null}
            className="flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-60"
            style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-primary)' }}
          >
            <FileText size={16} />
            {descargando === 'pdf' ? t('cuenta.descargando') : t('cuenta.descargarPdf')}
          </button>
          {!mostrarForm && (
            <button
              type="button"
              onClick={() => abrirNuevo()}
              className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: 'var(--yuda-primary)' }}
            >
              <Plus size={16} /> {t('cuenta.nuevo')}
            </button>
          )}
        </div>
      </div>

      {/* Saldo pendiente del cliente por moneda (no se suman monedas distintas) */}
      {cuenta.totales_por_moneda.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          {cuenta.totales_por_moneda.map((tm) => (
            <MetricCard
              key={tm.moneda}
              titulo={`${t('cuenta.saldoPendiente')} · ${tm.moneda}`}
              valor={fmtMon(tm.saldo_pendiente, tm.moneda)}
              icono={<Wallet size={20} />}
              color="var(--yuda-accent)"
            />
          ))}
        </div>
      )}

      {/* Formulario de alta/edición de movimiento */}
      {mostrarForm && (
        <div className="card rounded-lg border p-3" style={{ borderColor: 'var(--yuda-primary)' }}>
          <h3 className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-text)' }}>
            {editandoId ? t('cuenta.editar') : t('cuenta.nuevo')}
          </h3>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {/* Pedido (cotización) al que pertenece el movimiento */}
            <label className="flex flex-col gap-1 text-xs sm:col-span-2" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('cuenta.pedido')}
              <select value={form.sesion_id} onChange={(e) => cambiarPedido(e.target.value)} className="rounded-lg border px-2 py-1.5 text-sm" style={{ borderColor: 'var(--yuda-border)' }}>
                <option value="">{t('cuenta.sinPedido')}</option>
                {cotizaciones.map((s) => (
                  <option key={s.id} value={s.id}>
                    {numeroPedido(s)} · {s.pedido_estado ? t('cuenta.esPedido') : t('cuenta.esCotizacion')}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('cuenta.moneda')}
              <select
                value={form.moneda}
                onChange={(e) => setCampo('moneda', e.target.value)}
                disabled={!!monedaDelPedido(form.sesion_id)}
                className="rounded-lg border px-2 py-1.5 text-sm disabled:opacity-70"
                style={{ borderColor: 'var(--yuda-border)' }}
              >
                {MONEDAS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              {monedaDelPedido(form.sesion_id) && <span style={{ fontSize: 10 }}>{t('cuenta.monedaFijada')}</span>}
            </label>
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
            <Campo label={t('cuenta.montoOrigen')} type="number" value={form.monto_origen} onChange={(v) => setCampo('monto_origen', v)} hint={t('cuenta.montoOrigenAyuda')} />
            <label className="flex flex-col gap-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('cuenta.monedaOrigen')}
              <select
                value={form.moneda_origen}
                onChange={(e) => setCampo('moneda_origen', e.target.value)}
                className="rounded-lg border px-2 py-1.5 text-sm"
                style={{ borderColor: 'var(--yuda-border)' }}
              >
                {MONEDAS_ORIGEN.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </label>
            <Campo label={t('cuenta.tasa')} type="number" value={form.tasa_cambio} onChange={(v) => setCampo('tasa_cambio', v)} />
            <Campo
              label={t('cuenta.abono')}
              type="number"
              value={abonoCalculado !== null ? String(abonoCalculado) : form.abono}
              onChange={(v) => setCampo('abono', v)}
              hint={abonoCalculado !== null ? t('cuenta.abonoCalculado') : undefined}
            />
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

      {/* Un apartado por pedido, cada uno con su propio saldo */}
      {cuenta.pedidos.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cuenta.sinMovimientos')}</p>
      ) : (
        cuenta.pedidos.map((p) => (
          <section key={p.sesion_id ?? 'sin'} className="card flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Package size={16} style={{ color: 'var(--yuda-primary)' }} />
                <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>{tituloPedido(p)}</span>
                {p.sesion_id && (
                  <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={p.es_pedido
                    ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
                    : { backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}>
                    {p.es_pedido ? t('cuenta.esPedido') : t('cuenta.esCotizacion')}
                  </span>
                )}
                <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}>
                  {p.moneda}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('cuenta.saldoPendiente')}: <strong style={{ color: 'var(--yuda-accent)' }}>{fmtMon(p.saldo_pendiente, p.moneda)}</strong>
                </span>
                {p.sesion_id && (
                  <button type="button" onClick={() => abrirNuevo(p.sesion_id ?? '')} className="flex items-center gap-1 text-sm font-medium" style={{ color: 'var(--yuda-primary)' }}>
                    <Plus size={14} /> {t('cuenta.agregarAqui')}
                  </button>
                )}
              </div>
            </div>

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
                  {p.movimientos.map((m, i) => (
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
          </section>
        ))
      )}
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
