import { useTranslation } from 'react-i18next'
import { Check } from 'lucide-react'

// Barra de pasos: dice en que punto del proceso esta parada la vendedora, que ya
// quedo hecho y que falta. Se usa dos veces, con el mismo aspecto a proposito:
// para la secuencia de las fotos y para la cotizacion completa.
//
// `pasos` son claves de i18n; `activo` es el numero de paso (empieza en 1).
// Con `onIr` la barra tambien sirve para moverse: se puede tocar cualquier paso
// hasta `maxAlcanzable`, para volver atras sin perder de vista donde se estaba.
// `compacta` es para una barra anidada dentro de un paso: mas chica y sin
// numeros, para que se lea como sub-paso y no compita con la barra principal.
function BarraPasos({
  pasos,
  activo,
  onIr,
  maxAlcanzable,
  compacta,
}: {
  pasos: readonly string[]
  activo: number
  onIr?: (paso: number) => void
  maxAlcanzable?: number
  compacta?: boolean
}) {
  const { t } = useTranslation()
  const tope = maxAlcanzable ?? pasos.length
  const diametro = compacta ? 16 : 26
  return (
    <ol className="flex items-start">
      {pasos.map((clave, i) => {
        const numero = i + 1
        const hecho = numero < activo
        const actual = numero === activo
        const color = hecho
          ? 'var(--yuda-success)'
          : actual
            ? 'var(--yuda-primary)'
            : 'var(--yuda-border)'
        const navegable = Boolean(onIr) && numero <= tope
        return (
          <li key={clave} className="flex flex-1 flex-col items-center gap-1 text-center">
            <div className="flex w-full items-center">
              <span
                className="h-0.5 flex-1"
                style={{ backgroundColor: i === 0 ? 'transparent' : hecho || actual ? 'var(--yuda-success)' : 'var(--yuda-border)' }}
              />
              <button
                type="button"
                onClick={navegable ? () => onIr?.(numero) : undefined}
                disabled={!navegable}
                aria-current={actual ? 'step' : undefined}
                className="flex flex-shrink-0 items-center justify-center font-bold"
                style={{
                  cursor: navegable ? 'pointer' : 'default',
                  width: diametro,
                  height: diametro,
                  borderRadius: 999,
                  fontSize: 12,
                  border: `2px solid ${color}`,
                  backgroundColor: hecho || actual ? color : 'var(--yuda-white)',
                  color: hecho || actual ? 'var(--yuda-white)' : 'var(--yuda-text-secondary)',
                }}
              >
                {compacta ? null : hecho ? <Check size={14} /> : numero}
              </button>
              <span
                className="h-0.5 flex-1"
                style={{ backgroundColor: i === pasos.length - 1 ? 'transparent' : hecho ? 'var(--yuda-success)' : 'var(--yuda-border)' }}
              />
            </div>
            <span
              className="px-1"
              style={{
                fontSize: compacta ? 11 : 12,
                fontWeight: actual ? 700 : 500,
                color: actual ? 'var(--yuda-accent)' : 'var(--yuda-text-secondary)',
              }}
            >
              {t(clave)}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export default BarraPasos
