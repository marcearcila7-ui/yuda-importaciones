import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { AlertCircle, ArrowLeft, Check, ChevronDown, ChevronRight, Copy, Eye, EyeOff, KeyRound, Plus, RefreshCw, Search, Trash2, UserPlus, UserRound, Users, Wallet } from 'lucide-react'
import {
  actualizarCliente,
  crearCliente,
  eliminarCliente,
  getClientes,
  getCotizacionesCliente,
  resetPasswordCliente,
} from '../api/clientes'
import { eliminarSesion } from '../api/packing'
import { getEquipo } from '../api/admin'
import { useAuthStore } from '../store/authStore'
import { confirmar } from '../store/confirmStore'
import CredencialesCliente from '../components/CredencialesCliente'
import GestionPedidoCliente from '../components/GestionPedidoCliente'
import SeguimientoEditor from '../components/SeguimientoEditor'
import type { Cliente, ClienteCreado, ClienteCreate } from '../types/cliente'
import type { Sesion } from '../types/packing'
import type { EquipoResponse } from '../types/equipo'

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
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[var(--yuda-primary)] focus:outline-none'

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
    <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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
  const navigate = useNavigate()
  const esAdmin = useAuthStore((s) => s.usuario?.rol) === 'admin'
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [cargandoClientes, setCargandoClientes] = useState(true)
  const [errorClientes, setErrorClientes] = useState(false)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [guardando, setGuardando] = useState(false)
  const [credenciales, setCredenciales] = useState<ClienteCreado | null>(null)
  const [copiadoLink, setCopiadoLink] = useState(false)
  // Contraseña recién generada por cliente (solo en memoria, para reenviarla)
  const [nuevasPass, setNuevasPass] = useState<Record<string, string>>({})
  const portalUrl = `${window.location.origin}/portal/login`

  // Un solo cliente abierto a la vez, en su propia pantalla. Antes era un acordeon
  // dentro de la lista y quedaban tres niveles de cajas anidadas: cliente, acceso
  // al portal, cotizacion y seguimiento, todo apilado en la misma pagina.
  // Se guarda el id y no el objeto: si el cliente se borra o cambia de estado, la
  // pantalla se entera sola y vuelve a la lista.
  const [clienteAbiertoId, setClienteAbiertoId] = useState<string | null>(null)
  const [busqueda, setBusqueda] = useState('')
  // Solo para Marcela: a que vendedora pertenece cada cliente, y el filtro.
  // Antes esto vivia en una pagina aparte, "Equipo", que mostraba los mismos
  // clientes pero agrupados. Dos listas de lo mismo confunden mas de lo que ayudan.
  const [equipo, setEquipo] = useState<EquipoResponse | null>(null)
  const [filtroVendedora, setFiltroVendedora] = useState('')
  const [verInactivos, setVerInactivos] = useState(false)
  const [cotizaciones, setCotizaciones] = useState<Record<string, Sesion[]>>({})
  const [cotAbierta, setCotAbierta] = useState<Set<string>>(new Set())

  const [form, setForm] = useState<ClienteCreate>({ nombre: '', email: '' })

  const abrirCliente = (c: Cliente) => {
    setClienteAbiertoId(c.id)
    setCotAbierta(new Set())
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if (cotizaciones[c.id] === undefined) {
      getCotizacionesCliente(c.id)
        .then((cots) => setCotizaciones((m) => ({ ...m, [c.id]: cots })))
        .catch(() => setCotizaciones((m) => ({ ...m, [c.id]: [] })))
    }
  }

  const volverALista = () => {
    setClienteAbiertoId(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const recargarCotizaciones = (clienteId: string) => {
    getCotizacionesCliente(clienteId)
      .then((cots) => setCotizaciones((m) => ({ ...m, [clienteId]: cots })))
      .catch(() => {})
  }

  // Borrar una cotización del cliente. Si ya se la habían enviado, también deja
  // de verla en su portal.
  const eliminarCotizacion = async (s: Sesion, clienteId: string) => {
    const ok = await confirmar({
      mensaje: t('clientes.confirmarEliminarCotizacion', { numero: numeroCot(s) }),
      peligro: true,
      textoConfirmar: t('clientes.eliminarCotizacion'),
    })
    if (!ok) return
    try {
      await eliminarSesion(s.id)
      toast.success(t('clientes.cotizacionEliminada'))
      recargarCotizaciones(clienteId)
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      toast.error(typeof detalle === 'string' ? detalle : t('clientes.errorEliminarCotizacion'))
    }
  }

  const toggleCot = (id: string) => {
    const s = new Set(cotAbierta)
    s.has(id) ? s.delete(id) : s.add(id)
    setCotAbierta(s)
  }

  const cargar = () => {
    setCargandoClientes(true)
    setErrorClientes(false)
    getClientes()
      .then(setClientes)
      .catch(() => setErrorClientes(true))
      .finally(() => setCargandoClientes(false))
  }

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Marcela ve todos los clientes: necesita saber de quien es cada uno y poder
  // filtrar. Las vendedoras solo ven los suyos, asi que no hace falta pedirlo.
  useEffect(() => {
    if (!esAdmin) return
    getEquipo()
      .then(setEquipo)
      .catch(() => setEquipo({ vendedoras: [] }))
  }, [esAdmin])

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
        nit: form.nit?.trim() || undefined,
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
    const ok = await confirmar({
      mensaje: t('clientes.confirmarEliminar', { nombre: c.nombre }),
      peligro: true,
      textoConfirmar: t('clientes.eliminar'),
    })
    if (!ok) return
    try {
      await eliminarCliente(c.id)
      toast.success(t('clientes.eliminado'))
      cargar()
    } catch (err) {
      const estado = axios.isAxiosError(err) ? err.response?.status : null
      // 409: tiene cotizaciones enviadas y no se puede eliminar. En vez de dejar
      // a la vendedora sin salida, le ofrecemos desactivarlo en un clic.
      if (estado === 409) {
        if (await confirmar({ mensaje: t('clientes.ofrecerDesactivar', { nombre: c.nombre }), textoConfirmar: t('clientes.desactivar') })) {
          try {
            await actualizarCliente(c.id, { activo: false })
            toast.success(t('clientes.desactivado', { nombre: c.nombre }))
            cargar()
          } catch {
            toast.error(t('clientes.errorActualizar'))
          }
        }
        return
      }
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

  // Copia el acceso del cliente (link + correo, y la clave si se acaba de generar)
  const copiarCredenciales = async (c: Cliente) => {
    const pass = nuevasPass[c.id]
    let texto = `YUDA Importaciones — acceso a tu portal
${t('clientes.portalLink')}: ${portalUrl}
${t('clientes.email')}: ${c.email}`
    if (pass) texto += `\n${t('clientes.password')}: ${pass}`
    try {
      await navigator.clipboard.writeText(texto)
      toast.success(t('clientes.copiado'))
    } catch {
      toast.error(t('clientes.errorCopiar'))
    }
  }

  // Restablecer: como la contraseña actual no se puede ver (está encriptada),
  // genera una NUEVA y la revela en la ficha del cliente para reenviarla.
  const resetear = async (c: Cliente) => {
    if (!(await confirmar({ mensaje: t('clientes.confirmarReset', { nombre: c.nombre }) }))) return
    const nueva = generarPassword()
    try {
      await resetPasswordCliente(c.id, nueva)
      setNuevasPass((m) => ({ ...m, [c.id]: nueva }))
      toast.success(t('clientes.passwordReseteada'))
    } catch {
      toast.error(t('clientes.errorActualizar'))
    }
  }

  const vendedoras = equipo?.vendedoras ?? []
  const nombreVendedora: Record<string, string> = {}
  for (const v of vendedoras) nombreVendedora[v.user_id] = v.nombre

  // Cotizaciones esperando que Marcela cargue la naviera y el BL. Estaban en la
  // pagina "Equipo"; se traen aca, que es donde vive todo lo del cliente.
  const pendientesBl: { sesionId: string; numero: string; cliente: string; clienteId: string; vendedora: string }[] = []
  for (const v of vendedoras) {
    for (const c of v.clientes) {
      for (const cot of c.cotizaciones) {
        if (cot.pendiente_bl) {
          pendientesBl.push({
            sesionId: cot.sesion_id,
            numero: cot.numero,
            cliente: cot.nombre_cliente,
            clienteId: c.id,
            vendedora: v.nombre,
          })
        }
      }
    }
  }

  // Abre la ficha del cliente y despliega el seguimiento de esa cotizacion
  const abrirPendiente = (clienteId: string, sesionId: string) => {
    const cli = clientes.find((c) => c.id === clienteId)
    if (!cli) return
    abrirCliente(cli)
    setCotAbierta(new Set([sesionId]))
  }

  const inactivos = clientes.filter((c) => !c.activo).length

  const clienteAbierto = clientes.find((c) => c.id === clienteAbiertoId) ?? null

  const clientesFiltrados = (() => {
    const texto = busqueda.trim().toLowerCase()
    return clientes.filter((c) => {
      if (!c.activo && !verInactivos) return false
      if (filtroVendedora && c.vendedora_id !== filtroVendedora) return false
      if (!texto) return true
      return `${c.nombre} ${c.email} ${c.empresa ?? ''} ${c.pais ?? ''}`.toLowerCase().includes(texto)
    })
  })()

  // ---------- PANTALLA 2: la ficha de un cliente ----------
  if (clienteAbierto) {
    const c = clienteAbierto
    const cots = cotizaciones[c.id]
    return (
      <div className="flex flex-col gap-5">
        <button
          type="button"
          onClick={volverALista}
          className="flex items-center gap-2 self-start text-sm font-semibold"
          style={{ color: 'var(--yuda-primary)' }}
        >
          <ArrowLeft size={16} /> {t('clientes.volverALista')}
        </button>

        {/* Quien es y que se puede hacer con el */}
        <div className="card flex flex-col gap-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <span
                className="flex flex-shrink-0 items-center justify-center font-bold"
                style={{ width: 44, height: 44, borderRadius: 999, fontSize: 18, backgroundColor: 'var(--yuda-primary)', color: 'var(--yuda-white)' }}
              >
                {(c.nombre || '?').trim().charAt(0).toUpperCase()}
              </span>
              <div className="min-w-0">
                <h1 className="truncate" style={{ fontWeight: 700, fontSize: 22, color: 'var(--yuda-accent)' }}>
                  {c.nombre}
                </h1>
                <p className="truncate text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {[c.empresa, c.email, c.pais].filter(Boolean).join('  ')}
                </p>
              </div>
            </div>
            <span
              className="rounded-full px-3 py-1 text-xs font-semibold"
              style={
                c.activo
                  ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
                  : { backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }
              }
            >
              {c.activo ? t('clientes.activo') : t('clientes.inactivo')}
            </span>
          </div>

          <div className="flex flex-wrap gap-2 border-t border-gray-100 pt-3">
            <button
              type="button"
              onClick={() => navigate(`/clientes/${c.id}/cuenta`)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: 'var(--yuda-primary)' }}
            >
              <Wallet size={16} /> {t('cuentas.verCuenta')}
            </button>
            <button
              type="button"
              onClick={() => toggleActivo(c)}
              className="flex min-h-[42px] items-center rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: c.activo ? 'var(--yuda-error)' : 'var(--yuda-success)' }}
            >
              {c.activo ? t('clientes.desactivar') : t('clientes.activar')}
            </button>
            <button
              type="button"
              onClick={() => eliminar(c)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border px-4 text-sm font-semibold"
              style={{ borderColor: '#FCA5A5', color: 'var(--yuda-error)' }}
            >
              <Trash2 size={16} /> {t('clientes.eliminar')}
            </button>
          </div>
        </div>

        {/* Como entra este cliente a su portal */}
        <div className="card flex flex-col gap-3">
          <h2 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            {t('clientes.accesoTitulo')}
          </h2>
          <dl className="grid gap-2 text-sm sm:grid-cols-[130px_1fr]">
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.portalLink')}</dt>
            <dd className="break-all">
              <a href={portalUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--yuda-primary)' }}>
                {portalUrl}
              </a>
            </dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.email')}</dt>
            <dd className="break-all" style={{ color: 'var(--yuda-accent)' }}>{c.email}</dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.password')}</dt>
            <dd>
              {nuevasPass[c.id] ? (
                <span style={{ fontFamily: 'monospace', color: 'var(--yuda-accent)' }}>{nuevasPass[c.id]}</span>
              ) : (
                <span style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.passwordOculta')}</span>
              )}
            </dd>
          </dl>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => resetear(c)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: 'var(--yuda-primary)' }}
            >
              <KeyRound size={16} /> {t('clientes.resetPassword')}
            </button>
            <button
              type="button"
              onClick={() => copiarCredenciales(c)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: 'var(--yuda-success)' }}
            >
              <Copy size={16} /> {t('clientes.copiar')}
            </button>
          </div>
        </div>

        {/* Sus cotizaciones */}
        <div className="card flex flex-col gap-3">
          <h2 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            {t('clientes.cotizacionesTitulo')}
          </h2>

          {cots === undefined ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('equipo.cargando')}</p>
          ) : cots.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.sinCotizaciones')}</p>
          ) : (
            <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
              {cots.map((s) => (
                <div key={s.id} className="py-3 first:pt-0">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="flex flex-wrap items-center gap-2">
                        <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--yuda-accent)' }}>{numeroCot(s)}</span>
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-semibold"
                          style={
                            s.enviada_cliente
                              ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
                              : { backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }
                          }
                        >
                          {s.enviada_cliente ? t('clientes.enviada') : t('clientes.borrador')}
                        </span>
                        {s.pedido_recibido_at && (
                          <span
                            className="rounded-full px-2 py-0.5 text-xs font-semibold"
                            style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                          >
                            {t('clientes.pedidoRecibido')}
                          </span>
                        )}
                      </p>
                      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{s.fecha}</p>
                    </div>
                    <div className="flex flex-shrink-0 flex-wrap items-center gap-1">
                      <button type="button" onClick={() => navigate(`/cotizacion/${s.id}`)} className="min-h-[40px] rounded-lg px-3 text-sm font-semibold" style={{ color: 'var(--yuda-primary)' }}>
                        {t('clientes.verDetalle')}
                      </button>
                      <button type="button" onClick={() => toggleCot(s.id)} className="flex min-h-[40px] items-center gap-1 rounded-lg px-3 text-sm font-semibold" style={{ color: 'var(--yuda-primary)' }}>
                        {cotAbierta.has(s.id) ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                        {t('clientes.seguimiento')}
                      </button>
                      <button
                        type="button"
                        onClick={() => eliminarCotizacion(s, c.id)}
                        title={t('clientes.eliminarCotizacion')}
                        className="flex min-h-[40px] items-center rounded-lg px-3"
                        style={{ color: 'var(--yuda-error)' }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>

                  {s.pedido_recibido_at && (
                    <div className="mt-3">
                      <GestionPedidoCliente sesion={s} onActualizar={() => recargarCotizaciones(c.id)} />
                    </div>
                  )}
                  {cotAbierta.has(s.id) && (
                    <div className="mt-3">
                      <SeguimientoEditor sesionId={s.id} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // ---------- PANTALLA 1: la lista de clientes ----------
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>{t('clientes.titulo')}</h1>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.subtitulo')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setMostrarForm((v) => !v)}
          className="flex items-center gap-2 font-semibold text-white"
          style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
        >
          <UserPlus size={18} /> {t('clientes.nuevo')}
        </button>
      </div>

      {/* Lo que Marcela tiene que atender: cotizaciones esperando naviera y BL */}
      {esAdmin && pendientesBl.length > 0 && (
        <div className="rounded-xl border p-4" style={{ borderColor: '#FCD34D', backgroundColor: '#FFFBEB' }}>
          <p className="mb-2 flex items-center gap-2 text-sm font-bold" style={{ color: 'var(--yuda-warning-dark)' }}>
            <AlertCircle size={16} /> {t('equipo.pendientesBl', { n: pendientesBl.length })}
          </p>
          <div className="flex flex-col gap-1">
            {pendientesBl.map((p) => (
              <button
                key={p.sesionId}
                type="button"
                onClick={() => abrirPendiente(p.clienteId, p.sesionId)}
                className="flex flex-wrap items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-white"
                style={{ color: '#92400E' }}
              >
                <strong>{p.numero}</strong>
                <span>{p.cliente}</span>
                <span style={{ color: 'var(--yuda-warning-dark)' }}>({p.vendedora})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Credenciales recién creadas (incluye el link del portal) */}
      {credenciales && (
        <div className="card">
          <CredencialesCliente cliente={credenciales} onCerrar={() => setCredenciales(null)} />
        </div>
      )}

      {/* Formulario nuevo cliente */}
      {mostrarForm && (
        <div className="card flex flex-col gap-4">
          <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('clientes.nuevo')}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo label={t('clientes.nombre')} value={form.nombre} onChange={(v) => setCampo('nombre', v)} />
            <Campo label={t('clientes.email')} type="email" value={form.email} onChange={(v) => setCampo('email', v)} placeholder="cliente@correo.com" />
            <Campo label={t('clientes.empresa')} value={form.empresa ?? ''} onChange={(v) => setCampo('empresa', v)} />
            <Campo label={t('clientes.nit')} value={form.nit ?? ''} onChange={(v) => setCampo('nit', v)} />
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
              style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
            >
              <Plus size={18} /> {guardando ? t('clientes.creando') : t('clientes.crear')}
            </button>
            <button
              type="button"
              onClick={() => setMostrarForm(false)}
              className="rounded-lg px-4 text-sm font-medium"
              style={{ color: 'var(--yuda-text-secondary)' }}
            >
              {t('clientes.cancelar')}
            </button>
          </div>
        </div>
      )}

      {/* Lista de clientes */}
      <div className="card flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
            <Users size={18} /> {t('clientes.listaTitulo')}
          </h2>
          {clientes.length >= 6 && (
            <div className="relative">
              <Search size={16} className="absolute" style={{ left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--yuda-text-secondary)' }} />
              <input
                type="text"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder={t('clientes.buscar')}
                style={{ ...inputStyle, paddingLeft: 36 }}
                className={inputClase}
              />
            </div>
          )}
        </div>

        {/* Los desactivados estan guardados, no borrados: se ven cuando se piden */}
        {inactivos > 0 && (
          <button
            type="button"
            onClick={() => setVerInactivos((v) => !v)}
            className="flex items-center gap-2 self-start text-sm font-semibold"
            style={{ color: 'var(--yuda-text-secondary)' }}
          >
            {verInactivos ? <EyeOff size={15} /> : <Eye size={15} />}
            {verInactivos
              ? t('clientes.ocultarInactivos')
              : t('clientes.verInactivos', { n: inactivos })}
          </button>
        )}

        {/* De quien es cada cliente. Reemplaza a la pagina "Equipo": la misma
            informacion, pero como filtro sobre una unica lista. */}
        {esAdmin && vendedoras.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {[{ id: '', nombre: t('clientes.todasLasVendedoras') }, ...vendedoras.map((v) => ({ id: v.user_id, nombre: v.nombre }))].map((v) => {
              const activo = filtroVendedora === v.id
              const cuantos = v.id ? clientes.filter((c) => c.vendedora_id === v.id).length : clientes.length
              return (
                <button
                  key={v.id || 'todas'}
                  type="button"
                  onClick={() => setFiltroVendedora(v.id)}
                  className="flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold"
                  style={{
                    border: `1.5px solid ${activo ? 'var(--yuda-primary)' : 'var(--yuda-border)'}`,
                    backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'var(--yuda-white)',
                    color: activo ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
                  }}
                >
                  {v.nombre}
                  <span style={{ opacity: 0.7 }}>{cuantos}</span>
                </button>
              )
            })}
          </div>
        )}

        {cargandoClientes ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.cargando')}</p>
        ) : errorClientes ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm" style={{ color: 'var(--yuda-text)' }}>{t('clientes.errorCargar')}</p>
            <button
              type="button"
              onClick={cargar}
              className="flex items-center gap-2 rounded-lg px-4 font-semibold text-white"
              style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', fontSize: 15 }}
            >
              <RefreshCw size={16} /> {t('clientes.reintentar')}
            </button>
          </div>
        ) : clientes.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.sinClientes')}
          </p>
        ) : clientesFiltrados.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.sinResultados', { texto: busqueda })}
          </p>
        ) : (
          <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
            {clientesFiltrados.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => abrirCliente(c)}
                className="flex w-full items-center gap-3 py-3 text-left transition-colors first:pt-0 hover:bg-[var(--yuda-primary-soft)]"
              >
                <span
                  className="flex flex-shrink-0 items-center justify-center font-bold"
                  style={{ width: 38, height: 38, borderRadius: 999, fontSize: 15, backgroundColor: 'var(--yuda-primary)', color: 'var(--yuda-white)' }}
                >
                  {(c.nombre || '?').trim().charAt(0).toUpperCase()}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate" style={{ fontWeight: 600, fontSize: 15, color: 'var(--yuda-accent)' }}>
                    {c.nombre}
                  </span>
                  <span className="block truncate text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {[c.empresa, c.email].filter(Boolean).join('  ')}
                  </span>
                  {esAdmin && nombreVendedora[c.vendedora_id] && (
                    <span className="mt-0.5 flex items-center gap-1 text-xs" style={{ color: 'var(--yuda-primary)' }}>
                      <UserRound size={12} /> {nombreVendedora[c.vendedora_id]}
                    </span>
                  )}
                </span>
                {!c.activo && (
                  <span
                    className="flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold"
                    style={{ backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }}
                  >
                    {t('clientes.inactivo')}
                  </span>
                )}
                <ChevronRight size={18} style={{ color: 'var(--yuda-text-secondary)', flexShrink: 0 }} />
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Link del portal, al final: es informacion de referencia, no la tarea principal */}
      <div className="card flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>{t('clientes.portalTitulo')}</p>
          <a href={portalUrl} target="_blank" rel="noreferrer" className="break-all text-sm" style={{ color: 'var(--yuda-primary)' }}>
            {portalUrl}
          </a>
          <p className="mt-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.portalAyuda')}</p>
        </div>
        <button
          type="button"
          onClick={copiarLink}
          className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium"
          style={{ color: 'var(--yuda-primary)' }}
        >
          {copiadoLink ? <Check size={16} /> : <Copy size={16} />} {copiadoLink ? t('clientes.copiado') : t('clientes.copiarLink')}
        </button>
      </div>
    </div>
  )
}

export default Clientes
