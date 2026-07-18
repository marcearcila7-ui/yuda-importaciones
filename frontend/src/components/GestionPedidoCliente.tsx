import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { CheckCircle2, Clock, Package, Send } from 'lucide-react'
import { getItems } from '../api/packing'
import { enviarAConfirmar } from '../api/clientes'
import GenerarPedidos from './GenerarPedidos/GenerarPedidos'
import type { ItemResponse, Sesion } from '../types/packing'

// Gestión del pedido del cliente en el perfil del cliente (vendedora/Marcela):
// muestra las cantidades que pidió el cliente, permite ajustarlas y devolvérselas
// para confirmar, y —una vez confirmado— generar el pedido al proveedor.
function GestionPedidoCliente({ sesion, onActualizar }: { sesion: Sesion; onActualizar?: () => void }) {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState<ItemResponse[]>([])
  const [cantidades, setCantidades] = useState<Record<string, string>>({})
  const [estado, setEstado] = useState<string | null>(sesion.pedido_estado ?? null)
  const [enviando, setEnviando] = useState(false)

  useEffect(() => {
    if (!sesion.pedido_recibido_at) return
    getItems(sesion.id)
      .then((its) => {
        setItems(its)
        const init: Record<string, string> = {}
        its.forEach((it) => {
          if (it.cantidad_solicitada != null) init[it.id] = String(it.cantidad_solicitada)
        })
        setCantidades(init)
      })
      .catch(() => setItems([]))
  }, [sesion.id, sesion.pedido_recibido_at])

  if (!sesion.pedido_recibido_at) return null

  const descripcion = (it: ItemResponse): string =>
    (i18n.language === 'en' ? it.descripcion_en || it.descripcion_es : it.descripcion_es || it.descripcion_en) ||
    it.item_no ||
    '—'

  const confirmado = estado === 'confirmado'
  const porConfirmar = estado === 'por_confirmar'

  const badge = confirmado
    ? { txt: t('gestionPedido.estadoConfirmado'), bg: '#D1FAE5', fg: '#065F46', icon: <CheckCircle2 size={13} /> }
    : porConfirmar
      ? { txt: t('gestionPedido.estadoPorConfirmar'), bg: '#FEF3C7', fg: '#B45309', icon: <Clock size={13} /> }
      : { txt: t('gestionPedido.estadoRecibido'), bg: '#EEF0FD', fg: '#4B52E8', icon: <Package size={13} /> }

  const enviar = async () => {
    setEnviando(true)
    try {
      const payload = items.map((it) => ({ item_id: it.id, cantidad: Number(cantidades[it.id] || 0) }))
      const s = await enviarAConfirmar(sesion.id, payload)
      setEstado(s.pedido_estado ?? 'por_confirmar')
      toast.success(t('gestionPedido.enviadoAConfirmar'))
      onActualizar?.()
    } catch {
      toast.error(t('gestionPedido.error'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="rounded-xl border" style={{ borderColor: '#C7CBF7', backgroundColor: '#F5F6FE' }}>
      {/* Encabezado + estado */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5" style={{ borderColor: '#E0E2FA' }}>
        <p className="flex items-center gap-2 text-sm font-bold" style={{ color: '#4B52E8' }}>
          <Package size={16} /> {t('gestionPedido.titulo')}
        </p>
        <span
          className="flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold"
          style={{ backgroundColor: badge.bg, color: badge.fg }}
        >
          {badge.icon} {badge.txt}
        </span>
      </div>

      {/* Cantidades por producto (editables salvo cuando ya está confirmado) */}
      <div className="flex flex-col divide-y" style={{ borderColor: '#E5E7EB' }}>
        {items.map((it) => (
          <div key={it.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
            <span className="min-w-0 flex-1" style={{ color: '#0D0D0D' }}>{descripcion(it)}</span>
            {confirmado ? (
              <span className="flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold text-white" style={{ backgroundColor: '#10B981' }}>
                {cantidades[it.id] || 0} {t('gestionPedido.cajas')}
              </span>
            ) : (
              <div className="flex flex-shrink-0 items-center gap-1">
                <input
                  type="number"
                  min={0}
                  inputMode="numeric"
                  value={cantidades[it.id] ?? ''}
                  onChange={(e) => setCantidades((c) => ({ ...c, [it.id]: e.target.value }))}
                  className="w-20 rounded-lg border border-gray-200 px-2 py-1 text-right focus:border-[#4B52E8] focus:outline-none"
                  style={{ fontSize: 16 }}
                />
                <span className="text-xs" style={{ color: '#6B7280' }}>{t('gestionPedido.cajas')}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {sesion.notas_cliente && (
        <div className="border-t px-4 py-2.5 text-sm" style={{ borderColor: '#E0E2FA', color: '#374151' }}>
          <span className="font-semibold">📝 {t('gestionPedido.notas')}:</span> {sesion.notas_cliente}
        </div>
      )}

      {/* Acciones según el estado */}
      <div className="border-t px-4 py-3" style={{ borderColor: '#E0E2FA' }}>
        {confirmado ? (
          <div className="flex flex-col gap-3">
            <p className="flex items-center gap-2 text-sm font-medium" style={{ color: '#065F46' }}>
              <CheckCircle2 size={16} /> {t('gestionPedido.confirmadoOk')}
            </p>
            <p className="text-xs font-semibold" style={{ color: '#0D0D0D' }}>{t('gestionPedido.generarTitulo')}</p>
            <GenerarPedidos sesion_id={sesion.id} nombre_cliente={sesion.nombre_cliente} pedidoConfirmado />
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {porConfirmar && (
              <p className="flex items-center gap-2 text-sm" style={{ color: '#B45309' }}>
                <Clock size={15} /> {t('gestionPedido.esperandoConfirmacion')}
              </p>
            )}
            <p className="text-xs" style={{ color: '#6B7280' }}>{t('gestionPedido.avisoGenerar')}</p>
            <button
              type="button"
              onClick={enviar}
              disabled={enviando}
              className="flex min-h-[44px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: '#4B52E8', fontSize: 15 }}
            >
              <Send size={16} />{' '}
              {enviando
                ? t('gestionPedido.enviando')
                : porConfirmar
                  ? t('gestionPedido.reenviar')
                  : t('gestionPedido.enviarAConfirmar')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default GestionPedidoCliente
