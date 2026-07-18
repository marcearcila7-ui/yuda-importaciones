import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Link as LinkIcon, Plus, Send, UserCheck, UserPlus } from 'lucide-react'
import { crearCliente, enviarACliente, getClientes, vincularCliente } from '../../api/clientes'
import CredencialesCliente from '../CredencialesCliente'
import type { Cliente, ClienteCreado } from '../../types/cliente'

interface Props {
  sesionId: string
  clienteIdInicial: string | null
  enviadaInicial: boolean
  nombreClienteSesion?: string
}

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[var(--yuda-primary)] focus:outline-none'

function ClienteEnvio({ sesionId, clienteIdInicial, enviadaInicial, nombreClienteSesion }: Props) {
  const { t } = useTranslation()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [clienteId, setClienteId] = useState<string | null>(clienteIdInicial)
  const [enviada, setEnviada] = useState(enviadaInicial)
  const [seleccion, setSeleccion] = useState('')
  const [trabajando, setTrabajando] = useState(false)

  // Crear cliente nuevo directamente desde aquí
  const [creandoForm, setCreandoForm] = useState(false)
  const [guardandoCliente, setGuardandoCliente] = useState(false)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [nuevaPass, setNuevaPass] = useState('')
  const [credenciales, setCredenciales] = useState<ClienteCreado | null>(null)

  useEffect(() => {
    getClientes()
      .then(setClientes)
      .catch(() => undefined)
  }, [])

  // Sincroniza con la cotización seleccionada
  useEffect(() => {
    setClienteId(clienteIdInicial)
    setEnviada(enviadaInicial)
  }, [clienteIdInicial, enviadaInicial, sesionId])

  const clienteActual = clientes.find((c) => c.id === clienteId) || null

  const asignar = async () => {
    if (!seleccion) return
    setTrabajando(true)
    try {
      await vincularCliente(sesionId, seleccion)
      setClienteId(seleccion)
      toast.success(t('envio.clienteAsignado'))
    } catch {
      toast.error(t('envio.errorAsignar'))
    } finally {
      setTrabajando(false)
    }
  }

  const crearClienteInline = async () => {
    if (!nuevoNombre.trim() || !nuevoEmail.trim()) {
      toast.error(t('clientes.faltanDatos'))
      return
    }
    setGuardandoCliente(true)
    try {
      const creado = await crearCliente({
        nombre: nuevoNombre.trim(),
        email: nuevoEmail.trim(),
        password: nuevaPass.trim() || undefined,
      })
      setClientes((c) => [creado, ...c])
      await vincularCliente(sesionId, creado.id)
      setClienteId(creado.id)
      setCredenciales(creado)
      setCreandoForm(false)
      setNuevoEmail('')
      setNuevaPass('')
      toast.success(t('clientes.creado'))
    } catch (err) {
      const detalle =
        typeof err === 'object' && err && 'response' in err
          ? // @ts-expect-error acceso defensivo al detalle de axios
            err.response?.data?.detail
          : null
      toast.error(detalle || t('clientes.errorCrear'))
    } finally {
      setGuardandoCliente(false)
    }
  }

  const desvincular = async () => {
    setTrabajando(true)
    try {
      await vincularCliente(sesionId, null)
      setClienteId(null)
      setEnviada(false)
      setSeleccion('')
    } catch {
      toast.error(t('envio.errorAsignar'))
    } finally {
      setTrabajando(false)
    }
  }

  const enviar = async () => {
    setTrabajando(true)
    try {
      await enviarACliente(sesionId)
      setEnviada(true)
      toast.success(t('envio.enviada'))
    } catch {
      toast.error(t('envio.errorEnviar'))
    } finally {
      setTrabajando(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
        {t('envio.intro')}
      </p>

      {/* Asignar o crear cliente */}
      {!clienteActual ? (
        <div className="flex flex-col gap-3">
          {!creandoForm ? (
            <>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('envio.elegirCliente')}
                  <select
                    value={seleccion}
                    onChange={(e) => setSeleccion(e.target.value)}
                    style={inputStyle}
                    className={inputClase}
                  >
                    <option value="">{t('envio.selecciona')}</option>
                    {clientes.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} · {c.email}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  onClick={asignar}
                  disabled={trabajando || !seleccion}
                  className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
                  style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
                >
                  <LinkIcon size={18} /> {t('envio.asignar')}
                </button>
              </div>
              <button
                type="button"
                onClick={() => {
                  setNuevoNombre(nombreClienteSesion ?? '')
                  setCreandoForm(true)
                }}
                className="flex items-center gap-2 self-start text-sm font-semibold"
                style={{ color: 'var(--yuda-primary)' }}
              >
                <UserPlus size={16} /> {t('dashboard.crearClienteNuevo')}
              </button>
            </>
          ) : (
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                {t('clientes.nuevo')}
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                <input style={inputStyle} className={inputClase} placeholder={t('clientes.nombre')} value={nuevoNombre} onChange={(e) => setNuevoNombre(e.target.value)} />
                <input style={inputStyle} className={inputClase} type="email" placeholder={t('clientes.email')} value={nuevoEmail} onChange={(e) => setNuevoEmail(e.target.value)} />
                <input style={inputStyle} className={`${inputClase} sm:col-span-2`} placeholder={t('clientes.passwordOpcional')} value={nuevaPass} onChange={(e) => setNuevaPass(e.target.value)} />
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={crearClienteInline}
                  disabled={guardandoCliente}
                  className="flex items-center gap-2 font-semibold text-white disabled:opacity-60"
                  style={{ minHeight: 40, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 14px', fontSize: 14 }}
                >
                  <Plus size={16} /> {guardandoCliente ? t('clientes.creando') : t('clientes.crear')}
                </button>
                <button type="button" onClick={() => setCreandoForm(false)} className="text-sm font-medium" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('clientes.cancelar')}
                </button>
              </div>
            </div>
          )}

          {credenciales && <CredencialesCliente cliente={credenciales} onCerrar={() => setCredenciales(null)} />}
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl p-3" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
          <div className="flex items-center gap-2">
            <UserCheck size={18} style={{ color: 'var(--yuda-primary)' }} />
            <span className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>
              {clienteActual.nombre}
            </span>
            <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {clienteActual.email}
            </span>
          </div>
          {!enviada && (
            <button type="button" onClick={desvincular} className="text-sm font-medium" style={{ color: 'var(--yuda-error)' }}>
              {t('envio.cambiar')}
            </button>
          )}
        </div>
      )}

      {/* Enviar al cliente */}
      {clienteActual && !enviada && (
        <button
          type="button"
          onClick={enviar}
          disabled={trabajando}
          className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: 'var(--yuda-success)', borderRadius: 8, fontSize: 16 }}
        >
          <Send size={18} /> {t('envio.enviarBtn')}
        </button>
      )}

      {/* Ya enviada: el seguimiento se gestiona en Clientes */}
      {clienteActual && enviada && (
        <div className="rounded-xl p-3 text-sm" style={{ backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }}>
          <p className="flex items-center gap-2 font-semibold">
            <UserCheck size={16} /> {t('envio.yaEnviada')}
          </p>
          <p className="mt-1">
            {t('envio.trackingEnClientes')}{' '}
            <Link to="/clientes" style={{ color: '#047857', fontWeight: 600, textDecoration: 'underline' }}>
              {t('envio.irAClientes')}
            </Link>
          </p>
        </div>
      )}
    </div>
  )
}

export default ClienteEnvio
