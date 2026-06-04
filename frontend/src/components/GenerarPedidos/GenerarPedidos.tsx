import { useState } from 'react'
import type { CSSProperties } from 'react'
import axios from 'axios'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Download, FileText } from 'lucide-react'
import { descargarZip, generarPedidos } from '../../api/pedidos'
import type { GenerarPedidosResponse } from '../../types/pedidos'

interface GenerarPedidosProps {
  sesion_id: string
  nombre_cliente: string
}

const btnPrimario: CSSProperties = {
  minHeight: 48,
  backgroundColor: '#4B52E8',
  color: '#fff',
  borderRadius: 8,
  fontSize: 16,
  fontWeight: 600,
}

function GenerarPedidos({ sesion_id, nombre_cliente }: GenerarPedidosProps) {
  const { t } = useTranslation()
  const [generando, setGenerando] = useState(false)
  const [resultado, setResultado] = useState<GenerarPedidosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [descargandoZip, setDescargandoZip] = useState(false)

  const handleGenerar = async () => {
    const confirmado = window.confirm(t('pedidos.confirmar', { cliente: nombre_cliente }))
    if (!confirmado) return

    setError(null)
    setGenerando(true)
    try {
      const data = await generarPedidos(sesion_id)
      setResultado(data)
    } catch (err) {
      let mensaje = t('pedidos.errorGenerar')
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
    // En iPhone/Safari la pestaña debe abrirse dentro del toque (antes del await)
    const ventana = window.open('', '_blank')
    try {
      const blob = await descargarZip(sesion_id)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        const enlace = document.createElement('a')
        enlace.href = url
        enlace.download = `${nombre_cliente}_Pedidos.zip`
        enlace.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      ventana?.close()
      setError(t('pedidos.errorZip'))
    } finally {
      setDescargandoZip(false)
    }
  }

  return (
    <div className="flex w-full flex-col gap-4">
      {/* SECCIÓN A — Botón principal */}
      <button
        type="button"
        onClick={handleGenerar}
        disabled={generando}
        className="flex w-full items-center justify-center gap-2 disabled:opacity-60"
        style={btnPrimario}
      >
        {generando ? (
          t('pedidos.generando')
        ) : (
          <>
            <FileText size={18} /> {t('pedidos.generar')}
          </>
        )}
      </button>

      {/* SECCIÓN B — Advertencias */}
      {resultado && resultado.warnings.length > 0 && (
        <div className="rounded-xl p-4" style={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B' }}>
          <p className="flex items-center gap-2 font-bold" style={{ color: '#B45309' }}>
            <AlertTriangle size={18} /> {t('pedidos.advertencias')}
          </p>
          <ul className="mt-2 list-disc pl-5 text-sm" style={{ color: '#B45309' }}>
            {resultado.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* SECCIÓN C — Resultado */}
      {resultado && (
        <div className="flex flex-col gap-3">
          <p className="font-bold" style={{ color: '#0D0D0D' }}>{t('pedidos.generados')}</p>
          {resultado.pedidos.map((pedido) => (
            <div
              key={pedido.supplier}
              className="flex items-center justify-between rounded-xl p-3"
              style={{ backgroundColor: '#F9F9F7', border: '1px solid #E5E7EB' }}
            >
              <span className="text-sm" style={{ color: '#0D0D0D' }}>
                {pedido.supplier}{' '}
                <span style={{ color: '#9CA3AF' }}>({t('pedidos.itemsCount', { n: pedido.items_count })})</span>
              </span>
              <div className="flex flex-shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => window.open(pedido.url_descarga, '_blank')}
                  className="flex items-center gap-1 rounded-lg px-3 py-1 text-sm font-medium text-white"
                  style={{ backgroundColor: '#10B981' }}
                >
                  <Download size={16} /> {t('pedidos.descargarExcel')}
                </button>
                {pedido.url_pdf && (
                  <button
                    type="button"
                    onClick={() => window.open(pedido.url_pdf as string, '_blank')}
                    className="flex items-center gap-1 rounded-lg px-3 py-1 text-sm font-medium text-white"
                    style={{ backgroundColor: '#4B52E8' }}
                  >
                    <FileText size={16} /> {t('pedidos.descargarPdf')}
                  </button>
                )}
              </div>
            </div>
          ))}

          {resultado.pedidos.length > 1 && (
            <button
              type="button"
              onClick={handleDescargarZip}
              disabled={descargandoZip}
              className="w-full font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 48, backgroundColor: '#0D0D0D', borderRadius: 8, fontSize: 16 }}
            >
              {descargandoZip ? t('pedidos.preparandoZip') : t('pedidos.descargarZip')}
            </button>
          )}
        </div>
      )}

      {/* SECCIÓN D — Error */}
      {error && <p className="text-center text-sm" style={{ color: '#EF4444' }}>{error}</p>}
    </div>
  )
}

export default GenerarPedidos
