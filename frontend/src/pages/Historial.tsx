import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import { getHistorial } from '../api/admin'
import type { SesionHistorial } from '../types/admin'

const inputStyle: CSSProperties = { fontSize: 16 }
const botonStyle: CSSProperties = { minHeight: 48, fontSize: 16 }

function Historial() {
  const navigate = useNavigate()
  const [sesiones, setSesiones] = useState<SesionHistorial[]>([])
  const [cargando, setCargando] = useState(false)
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [nombreCliente, setNombreCliente] = useState('')

  const buscar = async () => {
    setCargando(true)
    try {
      const data = await getHistorial({
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        nombre_cliente: nombreCliente || undefined,
      })
      setSesiones(data)
    } finally {
      setCargando(false)
    }
  }

  // Cargar sin filtros al montar
  useEffect(() => {
    buscar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="min-h-screen bg-gray-100">
      <Navbar />

      <main className="mx-auto flex max-w-5xl flex-col gap-4 p-4">
        <h1 className="text-xl font-semibold text-gray-800">Historial de cotizaciones</h1>

        {/* Filtros */}
        <div className="flex flex-col gap-3 rounded border border-gray-200 bg-white p-4 sm:flex-row sm:items-end">
          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Desde
            <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)}
              style={inputStyle} className="rounded border border-gray-300 px-3 py-2" />
          </label>
          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Hasta
            <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)}
              style={inputStyle} className="rounded border border-gray-300 px-3 py-2" />
          </label>
          <label className="flex flex-1 flex-col gap-1 text-sm text-gray-700">
            Cliente
            <input type="text" value={nombreCliente} onChange={(e) => setNombreCliente(e.target.value)}
              style={inputStyle} className="rounded border border-gray-300 px-3 py-2" />
          </label>
          <button type="button" onClick={buscar} disabled={cargando} style={botonStyle}
            className="rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800 disabled:opacity-60">
            Buscar
          </button>
        </div>

        {/* Tabla */}
        {sesiones.length === 0 ? (
          <p className="mt-6 text-center text-gray-600">
            No hay cotizaciones que coincidan con los filtros
          </p>
        ) : (
          <div className="overflow-x-auto rounded border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-gray-100 text-left">
                <tr>
                  <th className="px-3 py-2">Fecha</th>
                  <th className="px-3 py-2">Cliente</th>
                  <th className="px-3 py-2 text-right">Ítems</th>
                  <th className="px-3 py-2 text-right">Total ¥</th>
                  <th className="px-3 py-2 text-right">Total USD</th>
                  <th className="px-3 py-2 text-right">Proveedores</th>
                  <th className="px-3 py-2">Pedidos generados</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {sesiones.map((s) => (
                  <tr key={s.id} className="border-t border-gray-100">
                    <td className="px-3 py-2">{s.fecha}</td>
                    <td className="px-3 py-2">{s.nombre_cliente}</td>
                    <td className="px-3 py-2 text-right">{s.total_items}</td>
                    <td className="px-3 py-2 text-right">{s.total_rmb.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right">{s.total_usd.toFixed(2)}</td>
                    <td className="px-3 py-2 text-right">{s.cantidad_proveedores}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${
                          s.tiene_pedidos ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-500'
                        }`}
                      >
                        {s.tiene_pedidos ? 'Sí' : 'No'}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <button
                        type="button"
                        onClick={() => navigate('/dashboard', { state: { sesion_id: s.id } })}
                        className="rounded bg-gray-200 px-3 py-1 font-medium text-gray-800 hover:bg-gray-300"
                      >
                        Ver detalle
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}

export default Historial
