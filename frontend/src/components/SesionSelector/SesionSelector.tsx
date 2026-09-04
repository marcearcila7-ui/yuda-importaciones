import { useEffect, useMemo, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { Check, FileText, Plus, Search, UserPlus, Users } from 'lucide-react'
import { usePackingStore } from '../../store/packingStore'
import { crearCliente, getClientes } from '../../api/clientes'
import { getConfiguracion } from '../../api/admin'
import CredencialesCliente from '../CredencialesCliente'
import type { Cliente, ClienteCreado } from '../../types/cliente'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

// La primera decisión de la cotización: cliente que ya existe, cliente nuevo, o
// ninguno todavía. Arranca sin elegir a propósito: mientras no se elija, no se
// muestra ningún formulario, y así queda claro que esto es lo primero que hay que hacer.
type Modo = 'existente' | 'nuevo' | 'libre'

// A partir de esta cantidad de clientes la lista se vuelve incómoda de recorrer
// a ojo y aparece el buscador.
const CLIENTES_PARA_BUSCADOR = 6

// Rótulo del paso, para que se vea que es una secuencia y no un formulario suelto
function Paso({ numero, titulo, children }: { numero: number; titulo: string; children: ReactNode }) {
  return (
    <div className="mt-5">
      <div className="flex items-center gap-2">
        <span
          className="flex items-center justify-center font-bold"
          style={{
            width: 22,
            height: 22,
            borderRadius: 999,
            fontSize: 12,
            backgroundColor: 'var(--yuda-primary)',
            color: 'var(--yuda-white)',
          }}
        >
          {numero}
        </span>
        <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>{titulo}</span>
      </div>
      <div className="mt-3">{children}</div>
    </div>
  )
}

// Tarjeta de opción del paso 1
function OpcionCard({
  activo,
  icono,
  titulo,
  ayuda,
  onClick,
}: {
  activo: boolean
  icono: ReactNode
  titulo: string
  ayuda: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full flex-col gap-1 text-left transition-colors"
      style={{
        minHeight: 96,
        padding: 14,
        borderRadius: 12,
        border: `2px solid ${activo ? 'var(--yuda-primary)' : 'var(--yuda-border)'}`,
        backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'var(--yuda-white)',
      }}
    >
      <span className="flex items-center gap-2" style={{ color: 'var(--yuda-primary)' }}>
        {icono}
        <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>{titulo}</span>
        {activo && <Check size={16} style={{ marginLeft: 'auto' }} />}
      </span>
      <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
        {ayuda}
      </span>
    </button>
  )
}

// Fila de cliente guardado
function FilaCliente({
  cliente,
  activo,
  onClick,
}: {
  cliente: Cliente
  activo: boolean
  onClick: () => void
}) {
  const inicial = (cliente.nombre || '?').trim().charAt(0).toUpperCase()
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-3 text-left transition-colors"
      style={{
        minHeight: 56,
        padding: '8px 12px',
        borderRadius: 10,
        border: `1px solid ${activo ? 'var(--yuda-primary)' : 'var(--yuda-border)'}`,
        backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'var(--yuda-white)',
      }}
    >
      <span
        className="flex items-center justify-center font-bold"
        style={{
          width: 34,
          height: 34,
          flexShrink: 0,
          borderRadius: 999,
          fontSize: 14,
          backgroundColor: 'var(--yuda-primary)',
          color: 'var(--yuda-white)',
        }}
      >
        {inicial}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate" style={{ fontWeight: 600, fontSize: 15, color: 'var(--yuda-accent)' }}>
          {cliente.nombre}
        </span>
        <span className="block truncate text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {cliente.empresa ? `${cliente.empresa}, ${cliente.email}` : cliente.email}
        </span>
      </span>
      {activo && <Check size={18} style={{ color: 'var(--yuda-primary)', flexShrink: 0 }} />}
    </button>
  )
}

function SesionSelector() {
  const { t } = useTranslation()
  const { isLoading, crearSesion } = usePackingStore()

  const [modo, setModo] = useState<Modo | null>(null)
  const [nombreLibre, setNombreLibre] = useState('')
  const [tipoCambio, setTipoCambio] = useState('6.7')
  const [aviso, setAviso] = useState<string | null>(null)

  // Clientes guardados de la cuenta
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [clienteSel, setClienteSel] = useState('')
  const [busqueda, setBusqueda] = useState('')

  // Crear cliente nuevo
  const [guardandoCliente, setGuardandoCliente] = useState(false)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [nuevaPass, setNuevaPass] = useState('')
  const [credenciales, setCredenciales] = useState<ClienteCreado | null>(null)

  useEffect(() => {
    getClientes()
      .then(setClientes)
      .catch(() => undefined)
    // Precargar el tipo de cambio que configuró la admin (evita cotizar con una
    // tasa vieja); si falla, queda el valor por defecto.
    getConfiguracion()
      .then((c) => setTipoCambio(String(c.tipo_cambio_usd)))
      .catch(() => undefined)
  }, [])

  const clientesFiltrados = useMemo(() => {
    const texto = busqueda.trim().toLowerCase()
    if (!texto) return clientes
    return clientes.filter((c) =>
      `${c.nombre} ${c.email} ${c.empresa ?? ''}`.toLowerCase().includes(texto),
    )
  }, [clientes, busqueda])

  const clienteElegido = clientes.find((c) => c.id === clienteSel) ?? null

  const elegirModo = (m: Modo) => {
    setModo(m)
    setAviso(null)
    // Cambiar de opción no debe arrastrar lo elegido en la anterior.
    if (m !== 'existente') setBusqueda('')
    if (m === 'libre') setClienteSel('')
    if (m === 'existente') setCredenciales(null)
  }

  const crearClienteNuevo = async () => {
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
      setClienteSel(creado.id)
      setCredenciales(creado)
      setNuevoNombre('')
      setNuevoEmail('')
      setNuevaPass('')
      setAviso(null)
      toast.success(t('clientes.creado'))
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      // Con la sesion vencida el interceptor ya manda al login, que lo explica:
      // mostrar aca "No autenticado" solo confunde.
      if (!axios.isAxiosError(err) || err.response?.status !== 401) {
        toast.error(detalle || t('clientes.errorCrear'))
      }
    } finally {
      setGuardandoCliente(false)
    }
  }

  const handleCrear = async () => {
    const tc = Number(tipoCambio) || 6.7
    if (!modo) {
      setAviso(t('dashboard.avisoElegirOpcion'))
      return
    }
    if (modo === 'libre') {
      if (!nombreLibre.trim()) {
        setAviso(t('dashboard.avisoNombre'))
        return
      }
      setAviso(null)
      await crearSesion(nombreLibre.trim(), tc, null)
      setNombreLibre('')
    } else {
      if (!clienteSel) {
        setAviso(modo === 'nuevo' ? t('dashboard.avisoCrearCliente') : t('dashboard.avisoElegirCliente'))
        return
      }
      setAviso(null)
      await crearSesion(clienteElegido?.nombre ?? '', tc, clienteSel)
    }
    setTipoCambio('6.7')
  }

  return (
    <div className="card">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
        {t('dashboard.nuevaCotizacion')}
      </h2>

      {/* PASO 1: la primera decisión, cliente que ya existe o cliente nuevo */}
      <Paso numero={1} titulo={t('dashboard.paraQuien')}>
        <div className="grid gap-3 sm:grid-cols-3">
          <OpcionCard
            activo={modo === 'existente'}
            icono={<Users size={18} />}
            titulo={t('dashboard.opcionExistente')}
            ayuda={
              clientes.length
                ? t('dashboard.opcionExistenteAyuda')
                : t('dashboard.opcionExistenteVacio')
            }
            onClick={() => elegirModo('existente')}
          />
          <OpcionCard
            activo={modo === 'nuevo'}
            icono={<UserPlus size={18} />}
            titulo={t('dashboard.opcionNuevo')}
            ayuda={t('dashboard.opcionNuevoAyuda')}
            onClick={() => elegirModo('nuevo')}
          />
          <OpcionCard
            activo={modo === 'libre'}
            icono={<FileText size={18} />}
            titulo={t('dashboard.opcionLibre')}
            ayuda={t('dashboard.opcionLibreAyuda')}
            onClick={() => elegirModo('libre')}
          />
        </div>
      </Paso>

      {/* PASO 2: depende de lo elegido arriba */}
      {modo === 'existente' && (
        <Paso numero={2} titulo={t('dashboard.elegirCliente')}>
          {clientes.length === 0 ? (
            <div
              className="flex flex-col items-start gap-2 p-4"
              style={{ borderRadius: 12, backgroundColor: 'var(--yuda-primary-soft)' }}
            >
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('dashboard.sinClientes')}
              </p>
              <button
                type="button"
                onClick={() => elegirModo('nuevo')}
                className="flex items-center gap-2 font-semibold text-white"
                style={{ minHeight: 40, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 14px', fontSize: 14 }}
              >
                <UserPlus size={16} /> {t('dashboard.crearPrimerCliente')}
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {clientes.length >= CLIENTES_PARA_BUSCADOR && (
                <div className="relative">
                  <Search
                    size={16}
                    className="absolute"
                    style={{ left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--yuda-text-secondary)' }}
                  />
                  <input
                    type="text"
                    value={busqueda}
                    onChange={(e) => setBusqueda(e.target.value)}
                    placeholder={t('dashboard.buscarCliente')}
                    style={{ ...inputStyle, paddingLeft: 36 }}
                    className={`${inputClase} min-h-[44px] w-full`}
                  />
                </div>
              )}

              <div className="flex flex-col gap-2" style={{ maxHeight: 280, overflowY: 'auto' }}>
                {clientesFiltrados.map((c) => (
                  <FilaCliente
                    key={c.id}
                    cliente={c}
                    activo={c.id === clienteSel}
                    onClick={() => {
                      setClienteSel(c.id)
                      setAviso(null)
                    }}
                  />
                ))}
                {clientesFiltrados.length === 0 && (
                  <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {t('dashboard.sinResultados', { texto: busqueda })}
                  </p>
                )}
              </div>
            </div>
          )}
        </Paso>
      )}

      {modo === 'nuevo' && (
        <Paso numero={2} titulo={t('clientes.nuevo')}>
          {clienteElegido ? (
            <div
              className="flex items-center gap-3 p-3"
              style={{ borderRadius: 12, border: '2px solid var(--yuda-primary)', backgroundColor: 'var(--yuda-primary-soft)' }}
            >
              <Check size={18} style={{ color: 'var(--yuda-primary)' }} />
              <span className="text-sm" style={{ color: 'var(--yuda-accent)' }}>
                {t('dashboard.clienteCreado', { nombre: clienteElegido.nombre })}
              </span>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <div className="grid gap-2 sm:grid-cols-2">
                <input style={inputStyle} className={`${inputClase} min-h-[44px]`} placeholder={t('clientes.nombre')} value={nuevoNombre} onChange={(e) => setNuevoNombre(e.target.value)} />
                <input style={inputStyle} className={`${inputClase} min-h-[44px]`} type="email" placeholder={t('clientes.email')} value={nuevoEmail} onChange={(e) => setNuevoEmail(e.target.value)} />
                <input style={inputStyle} className={`${inputClase} min-h-[44px] sm:col-span-2`} placeholder={t('clientes.passwordOpcional')} value={nuevaPass} onChange={(e) => setNuevaPass(e.target.value)} />
              </div>
              <button
                type="button"
                onClick={crearClienteNuevo}
                disabled={guardandoCliente}
                className="flex items-center gap-2 self-start font-semibold text-white disabled:opacity-60"
                style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 16px', fontSize: 15 }}
              >
                <Plus size={16} /> {guardandoCliente ? t('clientes.creando') : t('clientes.crear')}
              </button>
            </div>
          )}

          {credenciales && (
            <div className="mt-3">
              <CredencialesCliente cliente={credenciales} onCerrar={() => setCredenciales(null)} />
            </div>
          )}
        </Paso>
      )}

      {modo === 'libre' && (
        <Paso numero={2} titulo={t('dashboard.nombreCliente')}>
          <div className="flex flex-col gap-2">
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('dashboard.libreAyuda')}
            </p>
            <input
              type="text"
              value={nombreLibre}
              onChange={(e) => {
                setNombreLibre(e.target.value)
                if (aviso) setAviso(null)
              }}
              placeholder={t('dashboard.ejemploCliente')}
              style={inputStyle}
              className={`${inputClase} min-h-[48px]`}
            />
          </div>
        </Paso>
      )}

      {/* PASO 3: tipo de cambio y crear. Solo aparece con el paso 1 resuelto. */}
      {modo && (
        <Paso numero={3} titulo={t('dashboard.pasoCrear')}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
            <label className="flex flex-col gap-1 text-sm sm:w-44" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('dashboard.tipoCambio')}
              <input
                type="number"
                step="0.01"
                value={tipoCambio}
                onChange={(e) => setTipoCambio(e.target.value)}
                style={inputStyle}
                className={`${inputClase} min-h-[48px] w-full`}
              />
            </label>
            <button
              type="button"
              onClick={handleCrear}
              disabled={isLoading}
              className="min-h-[52px] w-full font-semibold text-white disabled:opacity-60 sm:min-h-[48px] sm:w-auto"
              style={{ backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
            >
              {isLoading ? t('dashboard.creando') : t('dashboard.nuevaCotizacion')}
            </button>
          </div>
        </Paso>
      )}

      {aviso && <p className="mt-3 text-sm" style={{ color: 'var(--yuda-error)' }}>{aviso}</p>}
    </div>
  )
}

export default SesionSelector
