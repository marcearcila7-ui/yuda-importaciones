import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { usePackingStore } from '../../store/packingStore'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none'

function SesionSelector() {
  const { sesiones, isLoading, cargarSesiones, crearSesion, seleccionarSesion } =
    usePackingStore()
  const [nombre, setNombre] = useState('')
  const [tipoCambio, setTipoCambio] = useState('6.7')
  const [aviso, setAviso] = useState<string | null>(null)

  // Carga las cotizaciones recientes al montar
  useEffect(() => {
    cargarSesiones()
  }, [cargarSesiones])

  const handleCrear = async () => {
    // Si falta el nombre del cliente, avisar en vez de no hacer nada
    if (!nombre.trim()) {
      setAviso('Escribe el nombre del cliente para crear la cotización.')
      return
    }
    setAviso(null)
    await crearSesion(nombre.trim(), Number(tipoCambio) || 6.7)
    setNombre('')
    setTipoCambio('6.7')
  }

  const recientes = sesiones.slice(0, 5)

  return (
    <div className="card">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>Nueva cotización</h2>
      <p className="mt-1 text-sm" style={{ color: '#6B7280' }}>
        Paso 1: escribe el nombre del cliente y toca «Nueva cotización». Después podrás
        subir fotos y armar la lista de productos.
      </p>

      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          Nombre del cliente
          <input
            type="text"
            value={nombre}
            onChange={(e) => {
              setNombre(e.target.value)
              if (aviso) setAviso(null)
            }}
            placeholder="Ej: Ferretería López"
            style={inputStyle}
            className={inputClase}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm sm:w-44" style={{ color: '#6B7280' }}>
          Tipo de cambio (RMB/USD)
          <input
            type="number"
            step="0.01"
            value={tipoCambio}
            onChange={(e) => setTipoCambio(e.target.value)}
            style={inputStyle}
            className={inputClase}
          />
        </label>
        <button
          type="button"
          onClick={handleCrear}
          disabled={isLoading}
          className="font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          {isLoading ? 'Creando...' : 'Nueva cotización'}
        </button>
      </div>

      {aviso && <p className="mt-2 text-sm" style={{ color: '#EF4444' }}>{aviso}</p>}

      {recientes.length > 0 && (
        <div className="mt-6">
          <p className="mb-2 text-sm font-medium" style={{ color: '#6B7280' }}>
            O abre una cotización que ya empezaste
          </p>
          <div className="flex flex-wrap gap-2">
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
