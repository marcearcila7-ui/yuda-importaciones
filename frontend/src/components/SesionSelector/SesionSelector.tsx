import { useEffect, useState } from 'react'
import type { CSSProperties, ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Check, FileText, Package, ShoppingBag, Users } from 'lucide-react'
import { usePackingStore } from '../../store/packingStore'
import { useAuthStore } from '../../store/authStore'
import { getClientes } from '../../api/clientes'
import { getConfiguracion } from '../../api/admin'
import SelectorCliente from '../SelectorCliente/SelectorCliente'
import type { Cliente } from '../../types/cliente'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

// La primera decisión de la cotización: cliente que ya existe, o ninguno
// todavía (cotización libre). Ya no se puede crear un cliente nuevo desde
// acá: todo cliente tiene que existir primero en Yuda Contable e importarse
// (pantalla de Clientes) -así Marcela mantiene un solo origen de clientes
// reales, sin duplicados sueltos creados a mano en el cotizador.
type Modo = 'existente' | 'libre'

// Qué se va a cotizar: cambia qué datos pide el OCR (bolsos necesita más rigor:
// tamaño, empaque, herrajes, riata, mínimos de la tienda, fotos de detalle).
type TipoCotizacion = 'productos' | 'bolsos'

// Encabezado de sección. Antes cada una llevaba un círculo numerado (1, 2, 3),
// pero este formulario es corto y de una sola pantalla, no un asistente largo:
// numerarlo como si lo fuera competía con el "Paso 1" real de arriba (el de
// Dashboard.tsx, que sí abarca toda la cotización) y sumaba una confusión más
// de "¿en qué paso estoy?" sin necesidad.
function Paso({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className="mt-5">
      <span style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>{titulo}</span>
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

function SesionSelector() {
  const { t } = useTranslation()
  const { isLoading, crearSesion } = usePackingStore()
  const { usuario } = useAuthStore()
  const esAdmin = usuario?.rol === 'admin'

  const [tipoCotizacion, setTipoCotizacion] = useState<TipoCotizacion | null>(null)
  const [modo, setModo] = useState<Modo | null>(null)
  const [nombreLibre, setNombreLibre] = useState('')
  const [tipoCambio, setTipoCambio] = useState('6.7')
  const [aviso, setAviso] = useState<string | null>(null)

  // Clientes guardados de la cuenta
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [cargandoClientes, setCargandoClientes] = useState(true)
  const [errorClientes, setErrorClientes] = useState(false)
  const [clienteSel, setClienteSel] = useState('')

  // Antes esto fallaba en silencio total: con mala señal en el mercado, la
  // lista de clientes se quedaba vacía para siempre, sin spinner ni error ni
  // forma de reintentar, y la vendedora no tenía cómo saber si seguía cargando
  // o si ya había fallado. Ahora se distingue cargando / error / vacío de verdad.
  const cargarClientes = () => {
    setCargandoClientes(true)
    setErrorClientes(false)
    getClientes()
      .then(setClientes)
      .catch(() => setErrorClientes(true))
      .finally(() => setCargandoClientes(false))
  }

  useEffect(() => {
    cargarClientes()
    // Precargar el tipo de cambio que configuró la admin (evita cotizar con una
    // tasa vieja); si falla, queda el valor por defecto.
    getConfiguracion()
      .then((c) => setTipoCambio(String(c.tipo_cambio_usd)))
      .catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const clienteElegido = clientes.find((c) => c.id === clienteSel) ?? null

  const elegirModo = (m: Modo) => {
    setModo(m)
    setAviso(null)
    // Cambiar de opción no debe arrastrar lo elegido en la anterior. (El texto
    // buscado vive dentro de SelectorCliente y se reinicia solo al desmontarse.)
    if (m === 'libre') setClienteSel('')
  }

  const elegirTipoCotizacion = (tp: TipoCotizacion) => {
    setTipoCotizacion(tp)
    setAviso(null)
  }

  const handleCrear = async () => {
    const tc = Number(tipoCambio) || 6.7
    if (!tipoCotizacion) {
      setAviso(t('dashboard.avisoQueCotizar'))
      return
    }
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
      await crearSesion(nombreLibre.trim(), tc, null, tipoCotizacion)
      setNombreLibre('')
    } else {
      if (!clienteSel) {
        setAviso(t('dashboard.avisoElegirCliente'))
        return
      }
      setAviso(null)
      await crearSesion(clienteElegido?.nombre ?? '', tc, clienteSel, tipoCotizacion)
    }
    setTipoCambio('6.7')
  }

  return (
    <div className="card">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
        {t('dashboard.nuevaCotizacion')}
      </h2>

      {/* PASO 0: qué se va a cotizar. Cambia qué datos pide el OCR más adelante. */}
      <Paso titulo={t('dashboard.queCotizar')}>
        <div className="grid gap-3 sm:grid-cols-2">
          <OpcionCard
            activo={tipoCotizacion === 'productos'}
            icono={<Package size={18} />}
            titulo={t('dashboard.opcionProductos')}
            ayuda={t('dashboard.opcionProductosAyuda')}
            onClick={() => elegirTipoCotizacion('productos')}
          />
          <OpcionCard
            activo={tipoCotizacion === 'bolsos'}
            icono={<ShoppingBag size={18} />}
            titulo={t('dashboard.opcionBolsos')}
            ayuda={t('dashboard.opcionBolsosAyuda')}
            onClick={() => elegirTipoCotizacion('bolsos')}
          />
        </div>
      </Paso>

      {/* PASO 1: la primera decisión, cliente que ya existe o cliente nuevo */}
      {tipoCotizacion && (
      <>
      <Paso titulo={t('dashboard.paraQuien')}>
        <div className="grid gap-3 sm:grid-cols-2">
          <OpcionCard
            activo={modo === 'existente'}
            icono={<Users size={18} />}
            titulo={t('dashboard.opcionExistente')}
            ayuda={
              cargandoClientes
                ? t('dashboard.opcionExistenteCargando')
                : clientes.length
                  ? t('dashboard.opcionExistenteAyuda')
                  : t('dashboard.opcionExistenteVacio')
            }
            onClick={() => elegirModo('existente')}
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
        <Paso titulo={t('dashboard.elegirCliente')}>
          {cargandoClientes ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('dashboard.cargandoClientes')}
            </p>
          ) : errorClientes ? (
            <div
              className="flex flex-col items-start gap-2 p-4"
              style={{ borderRadius: 12, backgroundColor: '#FEF2F2' }}
            >
              <p className="text-sm" style={{ color: 'var(--yuda-error-dark)' }}>
                {t('dashboard.errorCargarClientes')}
              </p>
              <button
                type="button"
                onClick={cargarClientes}
                className="flex items-center gap-2 font-semibold text-white"
                style={{ minHeight: 40, backgroundColor: 'var(--yuda-error)', borderRadius: 8, padding: '0 14px', fontSize: 14 }}
              >
                {t('dashboard.reintentarCargarClientes')}
              </button>
            </div>
          ) : clientes.length === 0 ? (
            <div
              className="flex flex-col items-start gap-2 p-4"
              style={{ borderRadius: 12, backgroundColor: 'var(--yuda-primary-soft)' }}
            >
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {esAdmin ? t('dashboard.sinClientesAdmin') : t('dashboard.sinClientesVendedora')}
              </p>
              {esAdmin && (
                <Link
                  to="/clientes"
                  className="flex items-center gap-2 font-semibold text-white"
                  style={{ minHeight: 40, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 14px', fontSize: 14 }}
                >
                  {t('dashboard.irAClientes')}
                </Link>
              )}
            </div>
          ) : (
            <SelectorCliente
              clientes={clientes}
              valor={clienteSel}
              onElegir={(id) => {
                setClienteSel(id)
                setAviso(null)
              }}
            />
          )}
        </Paso>
      )}

      {modo === 'libre' && (
        <Paso titulo={t('dashboard.nombreCliente')}>
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
        <Paso titulo={t('dashboard.pasoCrear')}>
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
      </>
      )}

      {aviso && <p className="mt-3 text-sm" style={{ color: 'var(--yuda-error)' }}>{aviso}</p>}
    </div>
  )
}

export default SesionSelector
