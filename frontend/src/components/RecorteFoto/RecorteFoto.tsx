import { useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Maximize2, RotateCcw, RotateCw, X } from 'lucide-react'

// Recuadro en fracciones de 0 a 1 sobre la foto original
type Recuadro = { x0: number; y0: number; x1: number; y1: number }

// Area minima para aceptar el recorte. Igual que la del backend: por debajo de
// esto seguro fue un toque sin querer, no un recuadro.
const AREA_MINIMA = 0.03

const limitar = (v: number) => Math.min(1, Math.max(0, v))

// Ajuste a mano del recorte, para cuando el automatico salio mal. La vendedora
// arrastra un recuadro sobre la foto original y el backend lo recorta con el
// mismo codigo que usa el OCR: aca solo se eligen las coordenadas.
function RecorteFoto({
  fotoUrl,
  recorteActual,
  guardando,
  onGuardar,
  onCerrar,
}: {
  fotoUrl: string
  // El recorte que hoy sale en los documentos. Sin esto la vendedora abria el
  // ajuste, veia la foto original entera y creia que no se habia recortado nada.
  recorteActual?: string | null
  guardando: boolean
  // recuadro null + giro 0 = volver a la foto completa; null + giro = solo girar
  onGuardar: (recuadro: number[] | null, giro: number) => void
  onCerrar: () => void
}) {
  const { t } = useTranslation()
  const contenedor = useRef<HTMLDivElement>(null)
  const [recuadro, setRecuadro] = useState<Recuadro | null>(null)
  const [arrastrando, setArrastrando] = useState(false)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  // Tamaño real de la foto (naturalWidth/Height), para saber dónde queda
  // dibujada DENTRO del contenedor. Sin esto no se puede calcular el recuadro.
  const [dimsFoto, setDimsFoto] = useState<{ w: number; h: number } | null>(null)

  // La foto se muestra con object-fit:contain: si su proporción no coincide con
  // la del contenedor, queda con franjas vacías arriba/abajo o a los costados
  // (una foto de celular, vertical, casi siempre las tiene a los lados). Antes
  // el recuadro se calculaba sobre el contenedor completo, franjas incluidas:
  // la vendedora arrastraba justo sobre el producto pero las coordenadas que se
  // guardaban quedaban corridas, así que el recorte final no era el que se veía
  // en pantalla. Esto calcula el rectángulo real donde cae la imagen.
  const cajaImagen = () => {
    const cont = contenedor.current?.getBoundingClientRect()
    if (!cont || cont.width === 0 || cont.height === 0 || !dimsFoto || !dimsFoto.w || !dimsFoto.h) {
      return null
    }
    const ratioFoto = dimsFoto.w / dimsFoto.h
    const ratioCaja = cont.width / cont.height
    let width: number
    let height: number
    if (ratioFoto > ratioCaja) {
      width = cont.width
      height = width / ratioFoto
    } else {
      height = cont.height
      width = height * ratioFoto
    }
    return {
      left: cont.left + (cont.width - width) / 2,
      top: cont.top + (cont.height - height) / 2,
      width,
      height,
      cont,
    }
  }

  const posicion = (e: ReactPointerEvent) => {
    const caja = cajaImagen()
    if (!caja || caja.width === 0 || caja.height === 0) return null
    return {
      x: limitar((e.clientX - caja.left) / caja.width),
      y: limitar((e.clientY - caja.top) / caja.height),
    }
  }

  const empezar = (e: ReactPointerEvent) => {
    const p = posicion(e)
    if (!p) return
    e.currentTarget.setPointerCapture(e.pointerId)
    inicio.current = p
    setArrastrando(true)
    setRecuadro({ x0: p.x, y0: p.y, x1: p.x, y1: p.y })
  }

  const mover = (e: ReactPointerEvent) => {
    if (!arrastrando || !inicio.current) return
    const p = posicion(e)
    if (!p) return
    setRecuadro({
      x0: Math.min(inicio.current.x, p.x),
      y0: Math.min(inicio.current.y, p.y),
      x1: Math.max(inicio.current.x, p.x),
      y1: Math.max(inicio.current.y, p.y),
    })
  }

  const terminar = () => {
    setArrastrando(false)
    inicio.current = null
  }

  const area = recuadro ? (recuadro.x1 - recuadro.x0) * (recuadro.y1 - recuadro.y0) : 0
  const sirve = area >= AREA_MINIMA

  // El recuadro se guarda en fracciones DE LA FOTO (lo que espera el backend),
  // pero se dibuja dentro del contenedor: si hay franjas vacías hay que
  // convertirlo a fracciones del contenedor antes de posicionarlo en pantalla.
  const cajaFoto = recuadro ? cajaImagen() : null
  const recuadroEnPantalla =
    recuadro && cajaFoto
      ? {
          x0: (cajaFoto.left - cajaFoto.cont.left + recuadro.x0 * cajaFoto.width) / cajaFoto.cont.width,
          y0: (cajaFoto.top - cajaFoto.cont.top + recuadro.y0 * cajaFoto.height) / cajaFoto.cont.height,
          x1: (cajaFoto.left - cajaFoto.cont.left + recuadro.x1 * cajaFoto.width) / cajaFoto.cont.width,
          y1: (cajaFoto.top - cajaFoto.cont.top + recuadro.y1 * cajaFoto.height) / cajaFoto.cont.height,
        }
      : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.8)' }}
      role="dialog"
      aria-modal="true"
    >
      <div className="flex max-h-[92vh] w-full max-w-3xl flex-col overflow-y-auto rounded-2xl bg-white p-5">
        <div className="mb-1 flex items-start justify-between gap-3">
          <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
            {t('recorte.titulo')}
          </h2>
          <button type="button" onClick={onCerrar} aria-label={t('recorte.cancelar')}>
            <X size={20} style={{ color: 'var(--yuda-text-secondary)' }} />
          </button>
        </div>
        <p className="mb-3 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('recorte.ayuda')}
        </p>

        {/* Girar: las fotos del mercado salen de costado porque se toman
            parandose al lado del producto */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('recorte.girar')}
          </span>
          <button
            type="button"
            onClick={() => onGuardar(null, 270)}
            disabled={guardando}
            aria-label={t('recorte.girarIzquierda')}
            className="flex items-center justify-center rounded-lg border disabled:opacity-50"
            style={{ width: 40, height: 40, borderColor: 'var(--yuda-border)', color: 'var(--yuda-primary)' }}
          >
            <RotateCcw size={18} />
          </button>
          <button
            type="button"
            onClick={() => onGuardar(null, 90)}
            disabled={guardando}
            aria-label={t('recorte.girarDerecha')}
            className="flex items-center justify-center rounded-lg border disabled:opacity-50"
            style={{ width: 40, height: 40, borderColor: 'var(--yuda-border)', color: 'var(--yuda-primary)' }}
          >
            <RotateCw size={18} />
          </button>
        </div>

        {recorteActual && (
          <div
            className="mb-3 flex items-center gap-3 rounded-lg p-2"
            style={{ backgroundColor: 'var(--yuda-primary-soft)' }}
          >
            <img
              src={recorteActual}
              alt=""
              style={{ width: 112, height: 112 }}
              className="flex-shrink-0 rounded-lg object-contain"
            />
            <span className="text-sm" style={{ color: 'var(--yuda-accent)' }}>
              {t('recorte.actual')}
            </span>
          </div>
        )}

        <div
          ref={contenedor}
          onPointerDown={empezar}
          onPointerMove={mover}
          onPointerUp={terminar}
          onPointerCancel={terminar}
          className="relative select-none overflow-hidden rounded-lg"
          style={{ touchAction: 'none', cursor: 'crosshair', backgroundColor: '#111' }}
        >
          <img
            src={fotoUrl}
            alt=""
            draggable={false}
            className="block w-full"
            style={{ maxHeight: '58vh', objectFit: 'contain' }}
            onLoad={(e) => {
              const img = e.currentTarget
              setDimsFoto({ w: img.naturalWidth, h: img.naturalHeight })
            }}
          />
          {recuadroEnPantalla && (
            <>
              {/* Oscurecer lo que queda fuera del recuadro */}
              <div
                className="pointer-events-none absolute inset-0"
                style={{
                  backgroundColor: 'rgba(0,0,0,0.55)',
                  clipPath: `polygon(0% 0%, 0% 100%, ${recuadroEnPantalla.x0 * 100}% 100%, ${recuadroEnPantalla.x0 * 100}% ${recuadroEnPantalla.y0 * 100}%, ${recuadroEnPantalla.x1 * 100}% ${recuadroEnPantalla.y0 * 100}%, ${recuadroEnPantalla.x1 * 100}% ${recuadroEnPantalla.y1 * 100}%, ${recuadroEnPantalla.x0 * 100}% ${recuadroEnPantalla.y1 * 100}%, ${recuadroEnPantalla.x0 * 100}% 100%, 100% 100%, 100% 0%)`,
                }}
              />
              <div
                className="pointer-events-none absolute"
                style={{
                  left: `${recuadroEnPantalla.x0 * 100}%`,
                  top: `${recuadroEnPantalla.y0 * 100}%`,
                  width: `${(recuadroEnPantalla.x1 - recuadroEnPantalla.x0) * 100}%`,
                  height: `${(recuadroEnPantalla.y1 - recuadroEnPantalla.y0) * 100}%`,
                  border: '2px solid var(--yuda-primary)',
                  boxShadow: '0 0 0 9999px rgba(0,0,0,0)',
                }}
              />
            </>
          )}
        </div>

        {recuadro && !sirve && (
          <p className="mt-2 text-sm" style={{ color: 'var(--yuda-error)' }}>
            {t('recorte.muyChico')}
          </p>
        )}

        <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={() => onGuardar(null, 0)}
            disabled={guardando}
            className="flex items-center justify-center gap-2 font-semibold disabled:opacity-50"
            style={{
              minHeight: 46,
              borderRadius: 8,
              padding: '0 16px',
              border: '2px solid var(--yuda-border)',
              color: 'var(--yuda-text-secondary)',
            }}
          >
            <Maximize2 size={16} /> {t('recorte.fotoCompleta')}
          </button>

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={onCerrar}
              disabled={guardando}
              className="font-medium disabled:opacity-50"
              style={{ minHeight: 46, padding: '0 16px', color: 'var(--yuda-text-secondary)' }}
            >
              {t('recorte.cancelar')}
            </button>
            <button
              type="button"
              onClick={() =>
                recuadro && onGuardar([recuadro.x0, recuadro.y0, recuadro.x1, recuadro.y1], 0)
              }
              disabled={!sirve || guardando}
              className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-50"
              style={{ minHeight: 46, borderRadius: 8, padding: '0 20px', backgroundColor: 'var(--yuda-primary)' }}
            >
              <Check size={18} /> {guardando ? t('recorte.guardando') : t('recorte.guardar')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default RecorteFoto
