import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHistorial } from '../api/admin'
import type { SesionHistorial } from '../types/admin'

const inputStyle: CSSProperties = { fontSize: 16 }

function fechaHoy(): string {
  const f = new Date().toLocaleDateString('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
  return f.charAt(0).toUpperCase() + f.slice(1)
}

const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none'

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
    <div className="flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>Historial de cotizaciones</h1>
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {fechaHoy()}
        </p>
      </div>

      {/* Filtros */}
      <div className="card flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          Desde
          <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          Hasta
          <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          Cliente
          <input type="text" value={nombreCliente} onChange={(e) => setNombreCliente(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <button
          type="button"
          onClick={buscar}
          disabled={cargando}
          className="font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          Buscar
        </button>
      </div>

      {/* Tabla */}
      {sesiones.length === 0 ? (
        <p className="mt-6 text-center" style={{ color: '#6B7280' }}>
          No hay cotizaciones que coincidan con los filtros
        </p>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead style={{ backgroundColor: '#0D0D0D', color: '#FFFFFF' }}>
              <tr>
                <th className="px-4 py-3 text-left font-semibold">Fecha</th>
                <th className="px-4 py-3 text-left font-semibold">Cliente</th>
                <th className="px-4 py-3 text-right font-semibold">Ítems</th>
                <th className="px-4 py-3 text-right font-semibold">Total ¥</th>
                <th className="px-4 py-3 text-right font-semibold">Total USD</th>
                <th className="px-4 py-3 text-right font-semibold">Proveedores</th>
                <th className="px-4 py-3 text-left font-semibold">Pedidos</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {sesiones.map((s, i) => (
                <tr key={s.id} style={{ backgroundColor: i % 2 === 0 ? '#FFFFFF' : '#F9F9F7' }}>
                  <td className="px-4 py-3">{s.fecha}</td>
                  <td className="px-4 py-3 font-medium">{s.nombre_cliente}</td>
                  <td className="px-4 py-3 text-right">{s.total_items}</td>
                  <td className="px-4 py-3 text-right">{s.total_rmb.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{s.total_usd.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{s.cantidad_proveedores}</td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-full px-3 py-1 text-xs font-semibold"
                      style={
                        s.tiene_pedidos
                          ? { backgroundColor: '#D1FAE5', color: '#065F46' }
                          : { backgroundColor: '#F3F4F6', color: '#6B7280' }
                      }
                    >
                      {s.tiene_pedidos ? 'Con pedidos' : 'Sin pedidos'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => navigate('/dashboard', { state: { sesion_id: s.id } })}
                      className="rounded-lg px-3 py-1 text-sm font-medium"
                      style={{ backgroundColor: '#EEF0FD', color: '#4B52E8' }}
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
    </div>
  )
}

export default Historial
