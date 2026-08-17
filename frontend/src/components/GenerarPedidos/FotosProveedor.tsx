import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Camera, Check, ChevronDown, ChevronRight, Image as ImageIcon } from 'lucide-react'
import { getItems, subirFotoFinal } from '../../api/packing'
import { ACCEPT_IMAGENES } from '../../lib/imagenes'
import type { ItemResponse } from '../../types/packing'

// La foto que verá el proveedor: la final (limpia) si existe, si no la de datos.
const fotoQueVeElProveedor = (item: ItemResponse) => item.foto_final_url || item.foto_url || null

function FilaProducto({
  item,
  sesionId,
  onSubida,
}: {
  item: ItemResponse
  sesionId: string
  onSubida: (actualizado: ItemResponse) => void
}) {
  const { t } = useTranslation()
  const input = useRef<HTMLInputElement>(null)
  const [subiendo, setSubiendo] = useState(false)

  const subir = async (archivo: File) => {
    setSubiendo(true)
    try {
      onSubida(await subirFotoFinal(sesionId, item.id, archivo))
      toast.success(t('packing.fotoFinalSubida'))
    } catch {
      toast.error(t('packing.fotoFinalError'))
    } finally {
      setSubiendo(false)
      if (input.current) input.current.value = ''
    }
  }

  const foto = fotoQueVeElProveedor(item)
  const tieneFinal = Boolean(item.foto_final_url)
  const descripcion = item.descripcion_es || item.descripcion_en || item.item_no || '—'

  return (
    <div className="flex items-center gap-3 py-2">
      {foto ? (
        <img
          src={foto}
          alt=""
          style={{ width: 72, height: 72 }}
          className="flex-shrink-0 rounded-lg object-cover"
        />
      ) : (
        <div
          style={{ width: 72, height: 72 }}
          className="flex flex-shrink-0 items-center justify-center rounded-lg bg-gray-100"
        >
          <ImageIcon size={22} style={{ color: 'var(--yuda-text-secondary)' }} />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium" style={{ color: 'var(--yuda-accent)' }}>
          {descripcion}
        </p>
        <p className="flex items-center gap-1 text-xs" style={{ color: tieneFinal ? 'var(--yuda-success)' : 'var(--yuda-text-secondary)' }}>
          {tieneFinal ? <Check size={13} /> : null}
          {tieneFinal ? t('fotosProveedor.conFotoFinal') : t('fotosProveedor.usaraFotoCarga')}
        </p>
      </div>

      <input
        ref={input}
        type="file"
        accept={ACCEPT_IMAGENES}
        className="hidden"
        onChange={(e) => {
          const archivo = e.target.files?.[0]
          if (archivo) subir(archivo)
        }}
      />
      <button
        type="button"
        onClick={() => input.current?.click()}
        disabled={subiendo}
        className="flex min-h-[40px] flex-shrink-0 items-center gap-1 rounded-lg border px-3 text-sm font-semibold disabled:opacity-60"
        style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)' }}
      >
        <Camera size={15} />
        {subiendo
          ? t('fotosProveedor.subiendo')
          : tieneFinal
            ? t('packing.fotoFinalCambiar')
            : t('packing.fotoFinalSubir')}
      </button>
    </div>
  )
}

/**
 * Fotos que llevará el pedido al proveedor. Va justo antes de generarlo porque
 * es el momento en que la vendedora decide con qué imagen se pide cada producto:
 * la foto final (limpia, sin el cartel de datos) es la referencia de lo que se
 * pidió si algo llega mal.
 */
function FotosProveedor({ sesionId }: { sesionId: string }) {
  const { t } = useTranslation()
  const [items, setItems] = useState<ItemResponse[] | null>(null)
  const [abierto, setAbierto] = useState(false)

  useEffect(() => {
    getItems(sesionId)
      .then(setItems)
      .catch(() => setItems([]))
  }, [sesionId])

  if (!items || items.length === 0) return null

  const conFotoFinal = items.filter((i) => i.foto_final_url).length

  return (
    <div className="rounded-xl border" style={{ borderColor: 'var(--yuda-border)' }}>
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-bold" style={{ color: 'var(--yuda-accent)' }}>
          <Camera size={16} /> {t('fotosProveedor.titulo')}
        </span>
        <span className="flex items-center gap-2">
          <span
            className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
            style={
              conFotoFinal === items.length
                ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }
                : { backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }
            }
          >
            {t('fotosProveedor.contador', { n: conFotoFinal, total: items.length })}
          </span>
          {abierto ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        </span>
      </button>

      {abierto && (
        <div className="border-t px-4 pb-3" style={{ borderColor: 'var(--yuda-border)' }}>
          <p className="py-3 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('fotosProveedor.ayuda')}
          </p>
          <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
            {items.map((item) => (
              <FilaProducto
                key={item.id}
                item={item}
                sesionId={sesionId}
                onSubida={(actualizado) =>
                  setItems((prev) =>
                    (prev ?? []).map((i) => (i.id === actualizado.id ? actualizado : i)),
                  )
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default FotosProveedor
