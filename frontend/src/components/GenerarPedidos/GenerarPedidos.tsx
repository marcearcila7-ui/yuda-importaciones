import { useState } from 'react'
import axios from 'axios'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Download, FileText, UserCheck } from 'lucide-react'
import { descargarZip, generarPedidos } from '../../api/pedidos'
import { confirmar } from '../../store/confirmStore'
import Button from '../ui/Button'
import type { GenerarPedidosResponse } from '../../types/pedidos'

interface GenerarPedidosProps {
  sesion_id: string
  nombre_cliente: string
  pedidoConfirmado?: boolean
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
      <Button variant="primary" size="lg" fullWidth onClick={() => handleGenerar(false)} disabled={generando !== false}>
        {generando === 'normal' ? (
          t('pedidos.generando')
        ) : (
          <>
            <FileText size={18} /> {t('pedidos.generar')}
          </>
        )}
      </Button>

      {/* Botón para generar con las cajas que pidió el cliente (Fase 3) */}
      {pedidoConfirmado && (
        <Button variant="success" size="lg" fullWidth onClick={() => handleGenerar(true)} disabled={generando !== false}>
          {generando === 'cliente' ? (
            t('pedidos.generando')
          ) : (
            <>
              <UserCheck size={18} /> {t('pedidos.generarCliente')}
            </>
          )}
        </Button>
      )}

      {/* SECCIÓN B — Advertencias */}
      {resultado && resultado.warnings.length > 0 && (
        <div className="rounded-xl p-4" style={{ backgroundColor: 'var(--yuda-warning-soft)', border: '1px solid var(--yuda-warning)' }}>
          <p className="flex items-center gap-2 font-bold" style={{ color: 'var(--yuda-warning-dark)' }}>
            <AlertTriangle size={18} /> {t('pedidos.advertencias')}
          </p>
          <ul className="mt-2 list-disc pl-5 text-sm" style={{ color: 'var(--yuda-warning-dark)' }}>
            {resultado.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* SECCIÓN C — Resultado */}
      {resultado && (
        <div className="flex flex-col gap-3">
          <p className="font-bold" style={{ color: 'var(--yuda-accent)' }}>{t('pedidos.generados')}</p>
          {resultado.pedidos.map((pedido) => (
            <div
              key={pedido.supplier}
              className="flex flex-col gap-2 rounded-xl p-3 sm:flex-row sm:items-center sm:justify-between"
              style={{ backgroundColor: '#F9F9F7', border: '1px solid var(--yuda-border)' }}
            >
              <span className="min-w-0 truncate text-sm" style={{ color: 'var(--yuda-accent)' }}>
                {pedido.supplier}{' '}
                <span style={{ color: 'var(--yuda-text-secondary)' }}>({t('pedidos.itemsCount', { n: pedido.items_count })})</span>
              </span>
              <div className="flex flex-shrink-0 gap-2">
                <button
                  type="button"
                  onClick={() => window.open(pedido.url_descarga, '_blank')}
                  className="flex min-h-[40px] flex-1 items-center justify-center gap-1 rounded-lg px-3 text-sm font-medium text-white sm:flex-none"
                  style={{ backgroundColor: 'var(--yuda-success)' }}
                >
                  <Download size={16} /> {t('pedidos.descargarExcel')}
                </button>
                {pedido.url_pdf && (
                  <button
                    type="button"
                    onClick={() => window.open(pedido.url_pdf as string, '_blank')}
                    className="flex min-h-[40px] flex-1 items-center justify-center gap-1 rounded-lg px-3 text-sm font-medium text-white sm:flex-none"
                    style={{ backgroundColor: 'var(--yuda-primary)' }}
                  >
                    <FileText size={16} /> {t('pedidos.descargarPdf')}
                  </button>
                )}
              </div>
            </div>
          ))}

          {resultado.pedidos.length > 1 && (
            <Button variant="dark" size="lg" fullWidth onClick={handleDescargarZip} disabled={descargandoZip}>
              {descargandoZip ? t('pedidos.preparandoZip') : t('pedidos.descargarZip')}
            </Button>
          )}
        </div>
      )}

      {/* SECCIÓN D — Error */}
      {error && <p className="text-center text-sm" style={{ color: 'var(--yuda-error)' }}>{error}</p>}
    </div>
  )
}

export default GenerarPedidos
