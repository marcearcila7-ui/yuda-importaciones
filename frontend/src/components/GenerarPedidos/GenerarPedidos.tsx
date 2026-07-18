import { useState } from 'react'
import type { CSSProperties } from 'react'
import axios from 'axios'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Download, FileText, UserCheck } from 'lucide-react'
import { descargarZip, generarPedidos } from '../../api/pedidos'
import { confirmar } from '../../store/confirmStore'
import type { GenerarPedidosResponse } from '../../types/pedidos'

interface GenerarPedidosProps {
  sesion_id: string
  nombre_cliente: string
  pedidoConfirmado?: boolean
}

const btnPrimario: CSSProperties = {
  minHeight: 48,
  backgroundColor: '#4B52E8',
  color: '#fff',
  borderRadius: 8,
  fontSize: 16,
  fontWeight: 600,
}

function GenerarPedidos({ sesion_id, nombre_cliente, pedidoConfirmado = false }: GenerarPedidosProps) {
  const { t } = useTranslation()
  const [generando, setGenerando] = useState<false | 'normal' | 'cliente'>(false)
  const [resultado, setResultado] = useState<GenerarPedidosResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [descargandoZip, setDescargandoZip] = useState(false)

  const handleGenerar = async (usarCantidadesCliente = false) => {
    let mensajeConfirm: string
    if (usarCantidadesCliente) {
      mensajeConfirm = t('pedidos.confirmarCliente', { cliente: nombre_cliente })
    } else if (!pedidoConfirmado) {
      // Botón normal (CTNS internas) cuando el cliente todavía no confirmó: advierte.
      mensajeConfirm = t('pedidos.confirmarSinPedido', { cliente: nombre_cliente })
    } else {
      mensajeConfirm = t('pedidos.confirmar', { cliente: nombre_cliente })
    }
    if (!(await confirmar(mensajeConfirm))) return

    setError(null)
    setGenerando(usarCantidadesCliente ? 'cliente' : 'normal')
    try {
      const data = await generarPedidos(sesion_id, usarCantidadesCliente)
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
      {/* SECCIÓN A — Botón principal (CTNS internas del packing) */}
      <button
        type="button"
        onClick={() => handleGenerar(false)}
        disabled={generando !== false}
        className="flex w-full items-center justify-center gap-2 disabled:opacity-60"
        style={btnPrimario}
      >
        {generando === 'normal' ? (
          t('pedidos.generando')
        ) : (
          <>
            <FileText size={18} /> {t('pedidos.generar')}
          </>
        )}
      </button>

      {/* Botón para generar con las cajas que pidió el cliente (Fase 3) */}
      {pedidoConfirmado && (
        <button
          type="button"
          onClick={() => handleGenerar(true)}
          disabled={generando !== false}
          className="flex w-full items-center justify-center gap-2 disabled:opacity-60"
          style={{ ...btnPrimario, backgroundColor: '#10B981' }}
        >
          {generando === 'cliente' ? (
            t('pedidos.generando')
          ) : (
            <>
              <UserCheck size={18} /> {t('pedidos.generarCliente')}
            </>
          )}
        </button>
      )}

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
              className="flex flex-col gap-2 rounded-xl p-3 sm:flex-row sm:items-center sm:justify-between"
              style={{ backgroundColor: '#F9F9F7', border: '1px solid #E5E7EB' }}
            >
              <span className="min-w-0 truncate text-sm" style={{ color: '#0D0D0D' }}>
                {pedido.supplier}{' '}
                <span style={{ color: '#6B7280' }}>({t('pedidos.itemsCount', { n: pedido.items_count })})</span>
              </span>
              <div className="flex flex-shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => window.open(pedido.url_descarga, '_blank')}
                  className="flex min-h-[40px] flex-1 items-center justify-center gap-1 rounded-lg px-3 text-sm font-medium text-white sm:flex-none"
                  style={{ backgroundColor: '#10B981' }}
                >
                  <Download size={16} /> {t('pedidos.descargarExcel')}
                </button>
                {pedido.url_pdf && (
                  <button
                    type="button"
                    onClick={() => window.open(pedido.url_pdf as string, '_blank')}
                    className="flex min-h-[40px] flex-1 items-center justify-center gap-1 rounded-lg px-3 text-sm font-medium text-white sm:flex-none"
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
