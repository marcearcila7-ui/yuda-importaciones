import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Info } from 'lucide-react'

interface Props {
  /** Valor que tiene ahora la casilla de mínimo */
  actual: number | null
  /** Mínimo de toda la tienda que leyó el OCR (null si el cartel no lo traía) */
  tienda?: number | null
  onElegir: (valor: number) => void
}

// Muchos carteles de Yiwu traen DOS mínimos: uno por modelo ("MOQ: 2 cajas por
// modelo") y otro por tienda ("toda tienda: 10 cajas"). La casilla es una sola, así
// que la app deja puesto el de por modelo y muestra el otro acá, a un toque.
//
// A propósito NO es una alerta que trabe: en una carga de 30 fotos serían 30 ventanas
// que cerrar, y lo que se cierra sin leer no sirve de nada. Se puede ir y volver entre
// los dos números las veces que haga falta.
function AvisoDosMinimos({ actual, tienda, onElegir }: Props) {
  const { t } = useTranslation()
  // El mínimo por modelo es el que trajo el OCR al principio; se recuerda para poder
  // volver a él después de haber cambiado al de la tienda.
  const [porModelo] = useState(actual)

  if (tienda == null || porModelo == null || tienda === porModelo) return null

  const usandoTienda = actual === tienda
  const otro = usandoTienda ? porModelo : tienda

  return (
    <div
      className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg px-2 py-1.5 text-xs"
      style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}
    >
      <Info size={14} className="flex-shrink-0" />
      <span>
        {usandoTienda
          ? t('ocr.usandoMinimoTienda', { n: tienda })
          : t('ocr.usandoMinimoModelo', { n: porModelo })}
      </span>
      <button
        type="button"
        onClick={() => onElegir(otro)}
        className="rounded-md px-2 py-0.5 font-semibold underline"
        style={{ color: 'var(--yuda-warning-dark)' }}
      >
        {usandoTienda
          ? t('ocr.cambiarAMinimoModelo', { n: porModelo })
          : t('ocr.cambiarAMinimoTienda', { n: tienda })}
      </button>
    </div>
  )
}

export default AvisoDosMinimos
