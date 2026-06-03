import { useState } from 'react'
import type { CSSProperties } from 'react'
import axios from 'axios'
import { descargarZip, generarPedidos } from '../../api/pedidos'
import type { GenerarPedidosResponse } from '../../types/pedidos'

interface GenerarPedidosProps {
  sesion_id: string
  nombre_cliente: string
}

const botonStyle: CSSProperties = { minHeight: 48, fontSize: 16 }

function GenerarPedidos({ sesion_id, nombre_cliente }: GenerarPedidosProps) {
  const [generando, setGenerando] = useState(false)
  const [resultado, setResultado] = useState<GenerarPedidosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [descargandoZip, setDescargandoZip] = useState(false)

  const handleGenerar = async () => {
    const confirmado = window.confirm(
      `¿Generar pedidos para ${nombre_cliente}? Se creará un archivo Excel por cada proveedor.`,
    )
    if (!confirmado) return

    setError(null)
    setGenerando(true)
    try {
      const data = await generarPedidos(sesion_id)
      setResultado(data)
    } catch (err) {
      let mensaje = 'No se pudieron generar los pedidos'
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        mensaje = err.response.data.detail
      }
      setError(mensaje)
    } finally {
      setGenerando(false)
    }
  }

  const handleDescargarZip = async () => {
    setError(null)
    setDescargandoZip(true)
    try {
      const blob = await descargarZip(sesion_id)
      const url = URL.createObjectURL(blob)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `${nombre_cliente}_Pedidos.zip`
      enlace.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('No se pudo descargar el ZIP')
    } finally {
      setDescargandoZip(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      {/* SECCIÓN A — Botón principal */}
      <button
        type="button"
        onClick={handleGenerar}
        disabled={generando}
        style={botonStyle}
        className="w-full rounded bg-green-600 px-4 font-semibold text-white hover:bg-green-700 disabled:opacity-60"
      >
        {generando ? 'Generando pedidos...' : 'Generar Pedidos'}
      </button>

      {/* SECCIÓN B — Advertencias */}
      {resultado && resultado.warnings.length > 0 && (
        <div className="rounded border border-yellow-300 bg-yellow-50 p-4">
          <p className="font-bold text-yellow-800">Advertencias:</p>
          <ul className="mt-2 list-disc pl-5 text-sm text-yellow-800">
            {resultado.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* SECCIÓN C — Resultado */}
      {resultado && (
        <div className="rounded border border-gray-200 bg-white p-4">
          <p className="font-bold text-gray-800">Pedidos generados:</p>
          <ul className="mt-2 flex flex-col gap-2">
            {resultado.pedidos.map((pedido) => (
              <li
                key={pedido.supplier}
                className="flex items-center justify-between rounded border border-gray-200 px-3 py-2"
              >
                <span className="text-sm text-gray-800">
                  {pedido.supplier}{' '}
                  <span className="text-gray-400">({pedido.items_count} ítems)</span>
                </span>
                <button
                  type="button"
                  onClick={() => window.open(pedido.url_descarga, '_blank')}
                  className="rounded bg-blue-700 px-3 py-1 text-sm font-medium text-white hover:bg-blue-800"
                >
                  Descargar Excel
                </button>
              </li>
            ))}
          </ul>

          {resultado.pedidos.length > 1 && (
            <button
              type="button"
              onClick={handleDescargarZip}
              disabled={descargandoZip}
              style={botonStyle}
              className="mt-4 w-full rounded bg-gray-700 px-4 font-semibold text-white hover:bg-gray-800 disabled:opacity-60"
            >
              {descargandoZip ? 'Preparando ZIP...' : 'Descargar todos (ZIP)'}
            </button>
          )}
        </div>
      )}

      {/* SECCIÓN D — Error */}
      {error && <p className="text-center text-sm text-red-600">{error}</p>}
    </div>
  )
}

export default GenerarPedidos
