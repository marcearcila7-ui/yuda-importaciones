import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Package } from 'lucide-react'
import { getItems } from '../api/packing'
import type { Sesion } from '../types/packing'

const LOCALES: Record<string, string> = { es: 'es-CO', en: 'en-US', zh: 'zh-CN' }

// Forma mínima de ítem que necesita el pedido del cliente.
interface ItemPedido {
  id: string
  item_no?: string | null
  descripcion_es?: string | null
  descripcion_en?: string | null
  cantidad_solicitada?: number | null
}

// Tarjeta clara y ordenada con lo que el cliente pidió al recibir la cotización:
// cajas por producto + sus notas. La ven la vendedora y Marcela por igual.
// - Si se le pasan `items`, los usa; si no, los carga por la sesión.
// - Si no hay pedido y `mostrarVacio` es true, muestra un aviso; si no, no renderiza nada.
function PedidoCliente({
  sesion,
  items: itemsProp,
  mostrarVacio = false,
}: {
  sesion: Sesion
  items?: ItemPedido[]
  mostrarVacio?: boolean
}) {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState<ItemPedido[]>(itemsProp ?? [])

  useEffect(() => {
    if (itemsProp) {
      setItems(itemsProp)
      return
    }
    if (sesion.pedido_recibido_at) {
      getItems(sesion.id)
        .then(setItems)
        .catch(() => setItems([]))
    }
  }, [sesion.id, sesion.pedido_recibido_at, itemsProp])

  const descripcion = (it: ItemPedido): string =>
    (i18n.language === 'en' ? it.descripcion_en || it.descripcion_es : it.descripcion_es || it.descripcion_en) ||
    it.item_no ||
    '—'

  if (!sesion.pedido_recibido_at) {
    if (!mostrarVacio) return null
    return (
      <div className="rounded-xl border p-3" style={{ borderColor: '#E5E7EB' }}>
        <p className="flex items-center gap-2 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
          <Package size={16} style={{ color: '#6B7280' }} /> {t('pedidoCliente.titulo')}
        </p>
        <p className="mt-1 text-sm" style={{ color: '#6B7280' }}>{t('pedidoCliente.sinPedido')}</p>
      </div>
    )
  }

  const fecha = new Date(sesion.pedido_recibido_at).toLocaleString(LOCALES[i18n.language] ?? 'es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })

  return (
    <div className="rounded-xl border" style={{ borderColor: '#C7CBF7', backgroundColor: '#F5F6FE' }}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b px-4 py-2.5" style={{ borderColor: '#E0E2FA' }}>
        <p className="flex items-center gap-2 text-sm font-bold" style={{ color: '#4B52E8' }}>
          <Package size={16} /> {t('pedidoCliente.titulo')}
        </p>
        <span className="text-xs" style={{ color: '#6B7280' }}>{t('pedidoCliente.recibidoEl', { fecha })}</span>
      </div>

      <div className="flex flex-col divide-y" style={{ borderColor: '#E5E7EB' }}>
        {items.map((it) => {
          const cajas = it.cantidad_solicitada ?? 0
          return (
            <div key={it.id} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
              <span className="min-w-0 flex-1" style={{ color: '#0D0D0D' }}>{descripcion(it)}</span>
              {cajas > 0 ? (
                <span className="flex-shrink-0 rounded-full px-2.5 py-0.5 text-xs font-bold text-white" style={{ backgroundColor: '#4B52E8' }}>
                  {t('pedidoCliente.cajas', { n: cajas })}
                </span>
              ) : (
                <span className="flex-shrink-0 text-xs" style={{ color: '#6B7280' }}>{t('pedidoCliente.sinCantidad')}</span>
              )}
            </div>
          )
        })}
      </div>

      {sesion.notas_cliente && (
        <div className="border-t px-4 py-2.5 text-sm" style={{ borderColor: '#E0E2FA', color: '#374151' }}>
          <span className="font-semibold">📝 {t('pedidoCliente.notas')}:</span> {sesion.notas_cliente}
        </div>
      )}
    </div>
  )
}

export default PedidoCliente
