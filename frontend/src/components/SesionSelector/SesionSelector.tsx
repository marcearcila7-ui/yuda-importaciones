import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Plus, UserPlus } from 'lucide-react'
import { usePackingStore } from '../../store/packingStore'
import { crearCliente, getClientes } from '../../api/clientes'
import { getConfiguracion } from '../../api/admin'
import CredencialesCliente from '../CredencialesCliente'
import type { Cliente, ClienteCreado } from '../../types/cliente'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

type Modo = 'cliente' | 'libre'

function SesionSelector() {
  const { t } = useTranslation()
  const { isLoading, crearSesion } = usePackingStore()

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
    getClientes()
      .then(setClientes)
      .catch(() => undefined)
    // Precargar el tipo de cambio que configuró la admin (evita cotizar con una
    // tasa vieja); si falla, queda el valor por defecto.
    getConfiguracion()
      .then((c) => setTipoCambio(String(c.tipo_cambio_usd)))
      .catch(() => undefined)
  }, [])

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
          backgroundColor: activo ? 'var(--yuda-primary)' : 'var(--yuda-primary-soft)',
          color: activo ? 'var(--yuda-white)' : 'var(--yuda-primary)',
        }}
      >
        {label}
      </button>
    )
  }

  return (
    <div className="card">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('dashboard.nuevaCotizacion')}</h2>
      <p className="mt-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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
              <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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

          {credenciales && (
            <CredencialesCliente cliente={credenciales} onCerrar={() => setCredenciales(null)} />
          )}
        </div>
      )}

      {/* MODO LIBRE */}
      {modo === 'libre' && (
        <div className="mt-4 flex flex-col gap-2">
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('dashboard.libreAyuda')}
          </p>
          <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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

      {aviso && <p className="mt-2 text-sm" style={{ color: 'var(--yuda-error)' }}>{aviso}</p>}

    </div>
  )
}

export default SesionSelector
