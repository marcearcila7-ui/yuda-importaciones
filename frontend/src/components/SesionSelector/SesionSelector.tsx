import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { usePackingStore } from '../../store/packingStore'

const inputStyle: CSSProperties = { fontSize: 16 }
const botonStyle: CSSProperties = { minHeight: 48, fontSize: 16 }

function SesionSelector() {
  const { sesiones, isLoading, cargarSesiones, crearSesion, seleccionarSesion } =
    usePackingStore()
  const [nombre, setNombre] = useState('')
  const [tipoCambio, setTipoCambio] = useState('6.7')

  // Carga las sesiones recientes al montar
  useEffect(() => {
    cargarSesiones()
  }, [cargarSesiones])

  const handleCrear = async () => {
    if (!nombre.trim()) return
    await crearSesion(nombre.trim(), Number(tipoCambio) || 6.7)
    setNombre('')
    setTipoCambio('6.7')
  }

  const recientes = sesiones.slice(0, 5)

  return (
    <div className="mx-auto w-full max-w-3xl rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1 text-sm text-gray-700">
          Nombre del cliente
          <input
            type="text"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            style={inputStyle}
            className="rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm text-gray-700 sm:w-32">
          Tipo de cambio
          <input
            type="number"
            step="0.01"
            value={tipoCambio}
            onChange={(e) => setTipoCambio(e.target.value)}
            style={inputStyle}
            className="rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
          />
        </label>
        <button
          type="button"
          onClick={handleCrear}
          disabled={isLoading || !nombre.trim()}
          style={botonStyle}
          className="rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
        >
          Nueva cotización
        </button>
      </div>

      {recientes.length > 0 && (
        <div className="mt-4">
          <p className="mb-2 text-sm font-medium text-gray-600">Cotizaciones recientes</p>
          <ul className="flex flex-col gap-2">
            {recientes.map((sesion) => (
              <li
                key={sesion.id}
                className="flex items-center justify-between rounded border border-gray-200 px-3 py-2"
              >
                <span className="text-sm text-gray-800">
                  {sesion.nombre_cliente}{' '}
                  <span className="text-gray-400">· TC {sesion.tipo_cambio_usd}</span>
                </span>
                <button
                  type="button"
                  onClick={() => seleccionarSesion(sesion)}
                  disabled={isLoading}
                  className="rounded bg-gray-200 px-3 py-1 text-sm font-medium text-gray-800 hover:bg-gray-300 disabled:opacity-60"
                >
                  Abrir
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default SesionSelector
