import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Plus, UserPlus } from 'lucide-react'
import { usePackingStore } from '../../store/packingStore'
import { crearCliente, getClientes } from '../../api/clientes'
import CredencialesCliente from '../CredencialesCliente'
import type { Cliente, ClienteCreado } from '../../types/cliente'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none'

type Modo = 'cliente' | 'libre'

function SesionSelector() {
  const { t } = useTranslation()
  const { sesiones, isLoading, cargarSesiones, crearSesion, seleccionarSesion } =
    usePackingStore()

  const [modo, setModo] = useState<Modo>('cliente')
  const [nombreLibre, setNombreLibre] = useState('')
  const [tipoCambio, setTipoCambio] = useState('6.7')
  const [aviso, setAviso] = useState<string | null>(null)

  // Clientes para el selector
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [clienteSel, setClienteSel] = useState('')

  // Crear cliente inline
  const [creandoForm, setCreandoForm] = useState(false)
  const [guardandoCliente, setGuardandoCliente] = useState(false)
  const [nuevoNombre, setNuevoNombre] = useState('')
  const [nuevoEmail, setNuevoEmail] = useState('')
  const [nuevaPass, setNuevaPass] = useState('')
  const [credenciales, setCredenciales] = useState<ClienteCreado | null>(null)

  useEffect(() => {
    cargarSesiones()
    getClientes()
      .then(setClientes)
      .catch(() => undefined)
  }, [cargarSesiones])

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
      setClienteSel(creado.id)
      setCredenciales(creado)
      setCreandoForm(false)
      setNuevoNombre('')
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

  const handleCrear = async () => {
    const tc = Number(tipoCambio) || 6.7
    if (modo === 'cliente') {
      if (!clienteSel) {
        setAviso(t('dashboard.avisoElegirCliente'))
        return
      }
      const cli = clientes.find((c) => c.id === clienteSel)
      setAviso(null)
      await crearSesion(cli?.nombre ?? '', tc, clienteSel)
    } else {
      if (!nombreLibre.trim()) {
        setAviso(t('dashboard.avisoNombre'))
        return
      }
      setAviso(null)
      await crearSesion(nombreLibre.trim(), tc, null)
      setNombreLibre('')
    }
    setTipoCambio('6.7')
  }

  const recientes = sesiones.slice(0, 5)

  const btnModo = (m: Modo, label: string) => {
    const activo = modo === m
    return (
      <button
        type="button"
        onClick={() => {
          setModo(m)
          setAviso(null)
        }}
        className="flex-1 font-semibold"
        style={{
          minHeight: 44,
          borderRadius: 8,
          fontSize: 15,
          backgroundColor: activo ? '#4B52E8' : '#EEF0FD',
          color: activo ? '#FFFFFF' : '#4B52E8',
        }}
      >
        {label}
      </button>
    )
  }

  return (
    <div className="card">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>{t('dashboard.nuevaCotizacion')}</h2>
      <p className="mt-1 text-sm" style={{ color: '#6B7280' }}>
        {t('dashboard.paraQuien')}
      </p>

      {/* Elegir tipo: para un cliente o libre */}
      <div className="mt-3 flex gap-2">
        {btnModo('cliente', t('dashboard.paraCliente'))}
        {btnModo('libre', t('dashboard.cotizacionLibre'))}
      </div>

      {/* MODO CLIENTE */}
      {modo === 'cliente' && (
        <div className="mt-4 flex flex-col gap-3">
          {!creandoForm ? (
            <>
              <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
                {t('dashboard.elegirCliente')}
                <select
                  value={clienteSel}
                  onChange={(e) => {
                    setClienteSel(e.target.value)
                    if (aviso) setAviso(null)
                  }}
                  style={inputStyle}
                  className={`${inputClase} min-h-[48px]`}
                >
                  <option value="">{t('dashboard.seleccionaCliente')}</option>
                  {clientes.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre} · {c.email}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={() => setCreandoForm(true)}
                className="flex items-center gap-2 self-start text-sm font-semibold"
                style={{ color: '#4B52E8' }}
              >
                <UserPlus size={16} /> {t('dashboard.crearClienteNuevo')}
              </button>
            </>
          ) : (
            <div className="rounded-xl border border-gray-200 p-3">
              <p className="mb-2 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
                {t('clientes.nuevo')}
              </p>
              <div className="grid gap-2 sm:grid-cols-2">
                <input style={inputStyle} className={`${inputClase} min-h-[44px]`} placeholder={t('clientes.nombre')} value={nuevoNombre} onChange={(e) => setNuevoNombre(e.target.value)} />
                <input style={inputStyle} className={`${inputClase} min-h-[44px]`} type="email" placeholder={t('clientes.email')} value={nuevoEmail} onChange={(e) => setNuevoEmail(e.target.value)} />
                <input style={inputStyle} className={`${inputClase} min-h-[44px] sm:col-span-2`} placeholder={t('clientes.passwordOpcional')} value={nuevaPass} onChange={(e) => setNuevaPass(e.target.value)} />
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={crearClienteInline}
                  disabled={guardandoCliente}
                  className="flex items-center gap-2 font-semibold text-white disabled:opacity-60"
                  style={{ minHeight: 40, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 14px', fontSize: 14 }}
                >
                  <Plus size={16} /> {guardandoCliente ? t('clientes.creando') : t('clientes.crear')}
                </button>
                <button type="button" onClick={() => setCreandoForm(false)} className="text-sm font-medium" style={{ color: '#6B7280' }}>
                  {t('clientes.cancelar')}
                </button>
              </div>
            </div>
          )}

          {credenciales && (
            <CredencialesCliente cliente={credenciales} onCerrar={() => setCredenciales(null)} />
          )}
        </div>
      )}

      {/* MODO LIBRE */}
      {modo === 'libre' && (
        <div className="mt-4 flex flex-col gap-2">
          <p className="text-sm" style={{ color: '#9CA3AF' }}>
            {t('dashboard.libreAyuda')}
          </p>
          <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
            {t('dashboard.nombreCliente')}
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
          </label>
        </div>
      )}

      {/* Tipo de cambio + crear */}
      <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-sm sm:w-44" style={{ color: '#6B7280' }}>
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
          style={{ backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          {isLoading ? t('dashboard.creando') : t('dashboard.nuevaCotizacion')}
        </button>
      </div>

      {aviso && <p className="mt-2 text-sm" style={{ color: '#EF4444' }}>{aviso}</p>}

      {recientes.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-sm font-medium" style={{ color: '#6B7280' }}>
            {t('dashboard.abrirReciente')}
          </p>
          {/* Mobile: cards verticales */}
          <div className="flex flex-col gap-2 sm:hidden">
            {recientes.map((sesion) => (
              <button
                key={sesion.id}
                type="button"
                onClick={() => seleccionarSesion(sesion)}
                disabled={isLoading}
                className="flex min-h-[48px] w-full items-center justify-between rounded-xl border border-gray-200 px-4 py-2 text-left disabled:opacity-60"
              >
                <span className="min-w-0">
                  <span className="block truncate font-semibold" style={{ color: '#0D0D0D' }}>
                    {sesion.nombre_cliente}
                  </span>
                  <span className="text-xs" style={{ color: '#9CA3AF' }}>
                    {sesion.fecha}
                  </span>
                </span>
                <span
                  className="ml-3 flex-shrink-0 rounded-full px-3 py-1 text-sm font-medium text-white"
                  style={{ backgroundColor: '#4B52E8' }}
                >
                  {t('dashboard.abrir')}
                </span>
              </button>
            ))}
          </div>

          {/* Desktop: chips en fila */}
          <div className="hidden flex-wrap gap-2 sm:flex">
            {recientes.map((sesion) => (
              <button
                key={sesion.id}
                type="button"
                onClick={() => seleccionarSesion(sesion)}
                disabled={isLoading}
                className="rounded-full px-4 py-2 text-sm font-medium transition-colors disabled:opacity-60"
                style={{ backgroundColor: '#EEF0FD', color: '#4B52E8' }}
              >
                {sesion.nombre_cliente}{' '}
                <span style={{ color: '#9CA3AF' }}>· TC {sesion.tipo_cambio_usd}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SesionSelector
