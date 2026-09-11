import { useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Maximize2, RotateCcw, RotateCw, X } from 'lucide-react'

// Recuadro en fracciones de 0 a 1, EN EL SISTEMA DE LA VISTA GIRADA (lo que la
// vendedora ve y arrastra en pantalla, no necesariamente la foto original).
type Recuadro = { x0: number; y0: number; x1: number; y1: number }
type Giro = 0 | 90 | 180 | 270

// Area minima para aceptar el recorte. Igual que la del backend: por debajo de
// esto seguro fue un toque sin querer, no un recuadro.
const AREA_MINIMA = 0.03

const limitar = (v: number) => Math.min(1, Math.max(0, v))

// El recuadro se dibuja sobre la vista YA GIRADA, pero el backend recorta sobre
// la foto ORIGINAL (sin girar) y gira después (ver backend/recorte_service.py).
// Esto traduce un punto de la vista girada a coordenadas de la foto original.
// Deducido geométricamente para cada giro posible (0/90/180/270, en sentido horario).
function aOriginal(u: number, v: number, giro: Giro): [number, number] {
  switch (giro) {
    case 90:
      return [v, 1 - u]
    case 180:
      return [1 - u, 1 - v]
    case 270:
      return [1 - v, u]
    default:
      return [u, v]
  }
}

// Ajuste a mano del recorte, para cuando el automatico salio mal. La vendedora
// gira y/o arrastra un recuadro sobre la foto, viendo siempre el resultado tal
// como va a quedar, y un solo botón manda los dos cambios juntos al backend
// (que recorta con el mismo código que usa el OCR).
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
  // Tamaño real de la foto ORIGINAL (naturalWidth/Height, sin girar).
  const [dimsFoto, setDimsFoto] = useState<{ w: number; h: number } | null>(null)
  // Giro elegido en ESTA sesión de edición. Antes cada click en girar guardaba
  // de inmediato en el backend pero la foto grande de acá abajo seguía
  // mostrándose sin girar (solo se actualizaba la miniatura de arriba): parecía
  // que girar no hacía nada, y si después se dibujaba un recorte, se aplicaba
  // sobre la foto SIN girar (se perdía el giro). Ahora el giro es local: se ve
  // al instante en la foto grande, y "Guardar" manda recorte + giro juntos.
  const [giro, setGiro] = useState<Giro>(0)

  // La foto se muestra girada `giro` grados: si esta rotación es de 90/270, lo
  // que ocupa el ancho y el alto se invierte. Esto calcula el rectángulo real
  // (en coordenadas de pantalla) donde cae la foto YA GIRADA dentro del
  // contenedor, para saber dónde caen los clics y dónde dibujar el recuadro.
  const cajaImagen = (giroActual: Giro) => {
    const cont = contenedor.current?.getBoundingClientRect()
    if (!cont || cont.width === 0 || cont.height === 0 || !dimsFoto?.w || !dimsFoto?.h) {
      return null
    }
    const girado = giroActual === 90 || giroActual === 270
    const anchoFoto = girado ? dimsFoto.h : dimsFoto.w
    const altoFoto = girado ? dimsFoto.w : dimsFoto.h
    const ratioFoto = anchoFoto / altoFoto
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
    const caja = cajaImagen(giro)
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

  // Gira la VISTA (no llama al backend): el guardado real pasa por "Guardar".
  // El recuadro ya dibujado se descarta: quedaría en el lugar equivocado sobre
  // la foto recién girada.
  const girar = (delta: 90 | -90) => {
    setGiro((g) => (((g + delta) % 360 + 360) % 360) as Giro)
    setRecuadro(null)
  }

  const area = recuadro ? (recuadro.x1 - recuadro.x0) * (recuadro.y1 - recuadro.y0) : 0
  const sirve = area >= AREA_MINIMA
  const hayCambio = (recuadro && sirve) || giro !== 0

  const guardar = () => {
    if (recuadro && sirve) {
      const [xa, ya] = aOriginal(recuadro.x0, recuadro.y0, giro)
      const [xb, yb] = aOriginal(recuadro.x1, recuadro.y1, giro)
      onGuardar([Math.min(xa, xb), Math.min(ya, yb), Math.max(xa, xb), Math.max(ya, yb)], giro)
    } else if (giro !== 0) {
      onGuardar(null, giro)
    }
  }

  const caja = cajaImagen(giro)
  const girado = giro === 90 || giro === 270

  // El recuadro se guarda en fracciones DE LA VISTA GIRADA, pero se dibuja
  // dentro del contenedor: si hay franjas vacías (la foto no llena el
  // contenedor) hay que convertirlo a fracciones del contenedor.
  const recuadroEnPantalla =
    recuadro && caja
      ? {
          x0: (caja.left - caja.cont.left + recuadro.x0 * caja.width) / caja.cont.width,
          y0: (caja.top - caja.cont.top + recuadro.y0 * caja.height) / caja.cont.height,
          x1: (caja.left - caja.cont.left + recuadro.x1 * caja.width) / caja.cont.width,
          y1: (caja.top - caja.cont.top + recuadro.y1 * caja.height) / caja.cont.height,
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
          {giro !== 0 ? t('recorte.ayudaGirada') : t('recorte.ayuda')}
        </p>

        {/* Girar: las fotos del mercado salen de costado porque se toman
            parandose al lado del producto. Se ve al instante en la foto de
            abajo; recién se guarda al tocar "Guardar". */}
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('recorte.girar')}
          </span>
          <button
            type="button"
            onClick={() => girar(-90)}
            disabled={guardando}
            aria-label={t('recorte.girarIzquierda')}
            className="flex items-center justify-center rounded-lg border disabled:opacity-50"
            style={{ width: 40, height: 40, borderColor: 'var(--yuda-border)', color: 'var(--yuda-primary)' }}
          >
            <RotateCcw size={18} />
          </button>
          <button
            type="button"
            onClick={() => girar(90)}
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
          style={{ touchAction: 'none', cursor: 'crosshair', backgroundColor: '#111', height: '58vh' }}
        >
          <img
            src={fotoUrl}
            alt=""
            draggable={false}
            onLoad={(e) => {
              const img = e.currentTarget
              setDimsFoto({ w: img.naturalWidth, h: img.naturalHeight })
            }}
            style={
              caja
                ? {
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    width: girado ? caja.height : caja.width,
                    height: girado ? caja.width : caja.height,
                    transform: `translate(-50%, -50%) rotate(${giro}deg)`,
                    objectFit: 'contain',
                  }
                : // Antes de saber el tamaño real de la foto (onLoad): visible pero
                  // sin medidas todavía, solo para que el navegador la cargue.
                  { display: 'block', maxWidth: '100%', maxHeight: '100%', margin: '0 auto' }
            }
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
              onClick={guardar}
              disabled={!hayCambio || guardando}
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
