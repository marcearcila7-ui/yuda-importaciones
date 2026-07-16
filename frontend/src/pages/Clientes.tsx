import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { Check, ChevronDown, ChevronRight, Copy, FileText, KeyRound, Plus, Trash2, UserPlus, Users } from 'lucide-react'
import {
  actualizarCliente,
  crearCliente,
  eliminarCliente,
  getClientes,
  getCotizacionesCliente,
  resetPasswordCliente,
} from '../api/clientes'
import CredencialesCliente from '../components/CredencialesCliente'
import SeguimientoEditor from '../components/SeguimientoEditor'
import type { Cliente, ClienteCreado, ClienteCreate } from '../types/cliente'
import type { Sesion } from '../types/packing'

const numeroCot = (s: Sesion) =>
  `YUDA-${(s.fecha || '').replace(/-/g, '')}-${s.id.slice(0, 6).toUpperCase()}`

// Genera una contraseña temporal legible (sin caracteres ambiguos) para reenviar
function generarPassword(): string {
  const abc = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  const arr = new Uint32Array(10)
  crypto.getRandomValues(arr)
  return Array.from(arr, (n) => abc[n % abc.length]).join('') + '*'
}

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[#4B52E8] focus:outline-none'

function Campo({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  placeholder?: string
}) {
  return (
    <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
      {label}
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={inputStyle}
        className={inputClase}
      />
    </label>
  )
}

function Clientes() {
  const { t } = useTranslation()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [mostrarForm, setMostrarForm] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [credenciales, setCredenciales] = useState<ClienteCreado | null>(null)
  const [copiadoLink, setCopiadoLink] = useState(false)
  const portalUrl = `${window.location.origin}/portal/login`

  // Expansión: cotizaciones del cliente + seguimiento
  const [expandido, setExpandido] = useState<Set<string>>(new Set())
  const [cotizaciones, setCotizaciones] = useState<Record<string, Sesion[]>>({})
  const [cotAbierta, setCotAbierta] = useState<Set<string>>(new Set())

  const [form, setForm] = useState<ClienteCreate>({ nombre: '', email: '' })

  const toggleCliente = (c: Cliente) => {
    const s = new Set(expandido)
    if (s.has(c.id)) {
      s.delete(c.id)
    } else {
      s.add(c.id)
      if (cotizaciones[c.id] === undefined) {
        getCotizacionesCliente(c.id)
          .then((cots) => setCotizaciones((m) => ({ ...m, [c.id]: cots })))
          .catch(() => setCotizaciones((m) => ({ ...m, [c.id]: [] })))
      }
    }
    setExpandido(s)
  }

  const toggleCot = (id: string) => {
    const s = new Set(cotAbierta)
    s.has(id) ? s.delete(id) : s.add(id)
    setCotAbierta(s)
  }

  const cargar = () =>
    getClientes()
      .then(setClientes)
      .catch(() => toast.error(t('clientes.errorCargar')))

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setCampo = (campo: keyof ClienteCreate, valor: string) =>
    setForm((f) => ({ ...f, [campo]: valor }))

  const handleCrear = async () => {
    if (!form.nombre.trim() || !form.email.trim()) {
      toast.error(t('clientes.faltanDatos'))
      return
    }
    setGuardando(true)
    try {
      const creado = await crearCliente({
        nombre: form.nombre.trim(),
        email: form.email.trim(),
        empresa: form.empresa?.trim() || undefined,
        pais: form.pais?.trim() || undefined,
        telefono: form.telefono?.trim() || undefined,
        password: form.password?.trim() || undefined,
      })
      setCredenciales(creado)
      setForm({ nombre: '', email: '' })
      setMostrarForm(false)
      toast.success(t('clientes.creado'))
      cargar()
    } catch (err) {
      const detalle =
        typeof err === 'object' && err && 'response' in err
          ? // @ts-expect-error acceso defensivo al detalle de axios
            err.response?.data?.detail
          : null
      toast.error(detalle || t('clientes.errorCrear'))
    } finally {
      setGuardando(false)
    }
  }

  const toggleActivo = async (c: Cliente) => {
    try {
      await actualizarCliente(c.id, { activo: !c.activo })
      cargar()
    } catch {
      toast.error(t('clientes.errorActualizar'))
    }
  }

  const eliminar = async (c: Cliente) => {
    if (!window.confirm(t('clientes.confirmarEliminar', { nombre: c.nombre }))) return
    try {
      await eliminarCliente(c.id)
      toast.success(t('clientes.eliminado'))
      cargar()
    } catch (err) {
      // 409: tiene cotizaciones enviadas → mostramos el mensaje del backend
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      toast.error(typeof detalle === 'string' ? detalle : t('clientes.errorEliminar'))
    }
  }

  const copiarLink = async () => {
    try {
      await navigator.clipboard.writeText(portalUrl)
      setCopiadoLink(true)
      setTimeout(() => setCopiadoLink(false), 2500)
    } catch {
      toast.error(t('clientes.errorCopiar'))
    }
  }

  // Restablecer: genera una contraseña nueva y muestra el bloque compartible
  // (link + correo + clave). Útil cuando la vendedora olvidó la contraseña.
  const resetear = async (c: Cliente) => {
    if (!window.confirm(t('clientes.confirmarReset', { nombre: c.nombre }))) return
    const nueva = generarPassword()
    try {
      await resetPasswordCliente(c.id, nueva)
      setCredenciales({ ...c, password_inicial: nueva })
      toast.success(t('clientes.passwordReseteada'))
    } catch {
      toast.error(t('clientes.errorActualizar'))
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>{t('clientes.titulo')}</h1>
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {t('clientes.subtitulo')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMostrarForm((v) => !v)}
          className="flex items-center gap-2 font-semibold text-white"
          style={{ minHeight: 44, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
        >
          <UserPlus size={18} /> {t('clientes.nuevo')}
        </button>
      </div>

      {/* Link del portal, siempre a mano para compartir con los clientes */}
      <div className="card flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p style={{ fontWeight: 700, fontSize: 15, color: '#0D0D0D' }}>{t('clientes.portalTitulo')}</p>
          <a href={portalUrl} target="_blank" rel="noreferrer" className="break-all text-sm" style={{ color: '#4B52E8' }}>
            {portalUrl}
          </a>
          <p className="mt-1 text-xs" style={{ color: '#9CA3AF' }}>{t('clientes.portalAyuda')}</p>
        </div>
        <button
          type="button"
          onClick={copiarLink}
          className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium"
          style={{ color: '#4B52E8' }}
        >
          {copiadoLink ? <Check size={16} /> : <Copy size={16} />} {copiadoLink ? t('clientes.copiado') : t('clientes.copiarLink')}
        </button>
      </div>

      {/* Credenciales recién creadas (incluye el link del portal) */}
      {credenciales && (
        <div className="card">
          <CredencialesCliente cliente={credenciales} onCerrar={() => setCredenciales(null)} />
        </div>
      )}

      {/* Formulario nuevo cliente */}
      {mostrarForm && (
        <div className="card flex flex-col gap-4">
          <h2 style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>{t('clientes.nuevo')}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo label={t('clientes.nombre')} value={form.nombre} onChange={(v) => setCampo('nombre', v)} />
            <Campo label={t('clientes.email')} type="email" value={form.email} onChange={(v) => setCampo('email', v)} placeholder="cliente@correo.com" />
            <Campo label={t('clientes.empresa')} value={form.empresa ?? ''} onChange={(v) => setCampo('empresa', v)} />
            <Campo label={t('clientes.pais')} value={form.pais ?? ''} onChange={(v) => setCampo('pais', v)} />
            <Campo label={t('clientes.telefono')} value={form.telefono ?? ''} onChange={(v) => setCampo('telefono', v)} />
            <Campo label={t('clientes.passwordOpcional')} value={form.password ?? ''} onChange={(v) => setCampo('password', v)} placeholder={t('clientes.passwordAuto')} />
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleCrear}
              disabled={guardando}
              className="flex items-center gap-2 font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 44, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
            >
              <Plus size={18} /> {guardando ? t('clientes.creando') : t('clientes.crear')}
            </button>
            <button
              type="button"
              onClick={() => setMostrarForm(false)}
              className="rounded-lg px-4 text-sm font-medium"
              style={{ color: '#6B7280' }}
            >
              {t('clientes.cancelar')}
            </button>
          </div>
        </div>
      )}

      {/* Lista de clientes */}
      <div className="card">
        <h2 className="mb-4 flex items-center gap-2" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
          <Users size={18} /> {t('clientes.listaTitulo')}
        </h2>

        {clientes.length === 0 ? (
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {t('clientes.sinClientes')}
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {clientes.map((c) => {
              const abierto = expandido.has(c.id)
              const cots = cotizaciones[c.id]
              return (
                <div key={c.id} className="rounded-xl border border-gray-200">
                  <div className="flex flex-wrap items-center justify-between gap-3 p-3">
                    <button type="button" onClick={() => toggleCliente(c)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
                      {abierto ? <ChevronDown size={18} style={{ color: '#9CA3AF' }} /> : <ChevronRight size={18} style={{ color: '#9CA3AF' }} />}
                      <div className="min-w-0">
                        <p className="font-semibold" style={{ color: '#0D0D0D' }}>
                          {c.nombre}
                          {c.empresa ? <span style={{ color: '#9CA3AF' }}> · {c.empresa}</span> : null}
                        </p>
                        <p className="text-sm" style={{ color: '#6B7280' }}>
                          {c.email}
                          {c.pais ? ` · ${c.pais}` : ''}
                        </p>
                      </div>
                    </button>
                    <div className="flex items-center gap-2">
                      <span
                        className="rounded-full px-2 py-0.5 text-xs font-semibold"
                        style={
                          c.activo
                            ? { backgroundColor: '#D1FAE5', color: '#10B981' }
                            : { backgroundColor: '#FEE2E2', color: '#EF4444' }
                        }
                      >
                        {c.activo ? t('clientes.activo') : t('clientes.inactivo')}
                      </span>
                      <button
                        type="button"
                        onClick={() => resetear(c)}
                        title={t('clientes.resetPassword')}
                        className="flex items-center gap-1 rounded-lg border border-gray-200 px-2 py-1 text-xs font-medium"
                        style={{ color: '#4B52E8' }}
                      >
                        <KeyRound size={14} /> {t('clientes.resetPassword')}
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleActivo(c)}
                        className="rounded-lg border border-gray-200 px-2 py-1 text-xs font-medium"
                        style={{ color: c.activo ? '#EF4444' : '#10B981' }}
                      >
                        {c.activo ? t('clientes.desactivar') : t('clientes.activar')}
                      </button>
                      <button
                        type="button"
                        onClick={() => eliminar(c)}
                        title={t('clientes.eliminar')}
                        className="flex items-center gap-1 rounded-lg border px-2 py-1 text-xs font-medium"
                        style={{ borderColor: '#FCA5A5', color: '#EF4444' }}
                      >
                        <Trash2 size={14} /> {t('clientes.eliminar')}
                      </button>
                    </div>
                  </div>

                  {/* Cotizaciones del cliente + seguimiento */}
                  {abierto && (
                    <div className="border-t border-gray-100 p-3">
                      {cots === undefined ? (
                        <p className="text-sm" style={{ color: '#9CA3AF' }}>{t('equipo.cargando')}</p>
                      ) : cots.filter((s) => s.enviada_cliente).length === 0 ? (
                        <p className="text-sm" style={{ color: '#9CA3AF' }}>{t('clientes.sinCotizacionesEnviadas')}</p>
                      ) : (
                        <div className="flex flex-col gap-2">
                          {cots.filter((s) => s.enviada_cliente).map((s) => (
                            <div key={s.id} className="rounded-lg" style={{ backgroundColor: '#F9FAFB' }}>
                              <div className="flex flex-wrap items-center justify-between gap-2 p-2">
                                <div className="flex items-center gap-2">
                                  <FileText size={15} style={{ color: '#6B7280' }} />
                                  <span className="text-sm font-medium" style={{ color: '#0D0D0D' }}>{numeroCot(s)}</span>
                                  <span className="text-xs" style={{ color: '#9CA3AF' }}>{s.fecha}</span>
                                </div>
                                <button type="button" onClick={() => toggleCot(s.id)} className="text-sm font-semibold" style={{ color: '#4B52E8' }}>
                                  {t('clientes.seguimiento')}
                                </button>
                              </div>
                              {cotAbierta.has(s.id) && (
                                <div className="border-t border-gray-100 p-3">
                                  <SeguimientoEditor sesionId={s.id} />
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

export default Clientes
