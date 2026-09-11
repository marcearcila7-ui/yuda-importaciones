import { useEffect, useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, Maximize2, RotateCcw, RotateCw, X } from 'lucide-react'

// Lado del cuadro de la vista previa en vivo.
const LADO_PREVIA = 112
// Lado al que se reescala la foto para dibujar la vista previa: no hace falta
// full resolucion para una miniatura de 112px, y así el redibujado en cada
// arrastre es instantáneo.
const LADO_TRABAJO_PREVIA = 500

// Dibuja, en vivo, cómo va a quedar la foto con el giro y el recuadro
// elegidos hasta ahora — girando primero (sobre un lienzo intermedio chico) y
// recortando después, igual que el backend (ver recortar_producto). Sin esto,
// la única referencia era una miniatura fija de "cómo sale hoy" que no se
// movía mientras se editaba, y parecía que el sistema ignoraba los cambios.
function dibujarPrevia(
  canvas: HTMLCanvasElement | null,
  img: HTMLImageElement | null,
  dimsFoto: { w: number; h: number } | null,
  giro: Giro,
  recuadro: Recuadro | null,
) {
  if (!canvas || !img || !dimsFoto?.w || !dimsFoto?.h) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, LADO_PREVIA, LADO_PREVIA)

  const escalaTrabajo = LADO_TRABAJO_PREVIA / Math.max(dimsFoto.w, dimsFoto.h)
  const tw = Math.max(1, Math.round(dimsFoto.w * escalaTrabajo))
  const th = Math.max(1, Math.round(dimsFoto.h * escalaTrabajo))
  const girado = giro === 90 || giro === 270
  const rw = girado ? th : tw
  const rh = girado ? tw : th

  const girada = document.createElement('canvas')
  girada.width = rw
  girada.height = rh
  const ctxGirada = girada.getContext('2d')
  if (!ctxGirada) return
  ctxGirada.translate(rw / 2, rh / 2)
  ctxGirada.rotate((giro * Math.PI) / 180)
  ctxGirada.drawImage(img, -tw / 2, -th / 2, tw, th)

  const x0 = recuadro ? recuadro.x0 : 0
  const y0 = recuadro ? recuadro.y0 : 0
  const x1 = recuadro ? recuadro.x1 : 1
  const y1 = recuadro ? recuadro.y1 : 1
  const sx = x0 * rw
  const sy = y0 * rh
  const sw = Math.max(1, (x1 - x0) * rw)
  const sh = Math.max(1, (y1 - y0) * rh)
  const escalaPrevia = Math.min(LADO_PREVIA / sw, LADO_PREVIA / sh)
  const dw = sw * escalaPrevia
  const dh = sh * escalaPrevia
  ctx.drawImage(girada, sx, sy, sw, sh, (LADO_PREVIA - dw) / 2, (LADO_PREVIA - dh) / 2, dw, dh)
}

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

// Inversa de aOriginal: de coordenadas de la foto original a la vista girada.
function deOriginal(x: number, y: number, giro: Giro): [number, number] {
  switch (giro) {
    case 90:
      return [1 - y, x]
    case 180:
      return [1 - x, 1 - y]
    case 270:
      return [y, 1 - x]
    default:
      return [x, y]
  }
}

// Recalcula el recuadro dibujado bajo un giro a como se ve bajo OTRO giro,
// en vez de borrarlo: girar no debería obligar a recortar de nuevo.
function recuadroTrasGirar(r: Recuadro, giroViejo: Giro, giroNuevo: Giro): Recuadro {
  const esquinas = (
    [
      [r.x0, r.y0],
      [r.x1, r.y0],
      [r.x1, r.y1],
      [r.x0, r.y1],
    ] as const
  ).map(([u, v]) => deOriginal(...aOriginal(u, v, giroViejo), giroNuevo))
  const xs = esquinas.map((p) => p[0])
  const ys = esquinas.map((p) => p[1])
  return { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) }
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
  const imgRef = useRef<HTMLImageElement>(null)
  const previaRef = useRef<HTMLCanvasElement>(null)
  const [recuadro, setRecuadro] = useState<Recuadro | null>(null)
  const inicio = useRef<{ x: number; y: number } | null>(null)
  // Qué está arrastrando la vendedora ahora mismo: un recuadro nuevo desde
  // cero, el recuadro entero (moverlo sin cambiar su tamaño), o una esquina
  // (agrandar/achicar desde esa esquina, con la opuesta fija como ancla).
  const modo = useRef<
    | { tipo: 'nuevo' }
    | { tipo: 'mover'; dx: number; dy: number }
    | { tipo: 'esquina'; anclaX: number; anclaY: number }
    | null
  >(null)
  // Tamaño real de la foto ORIGINAL (naturalWidth/Height, sin girar).
  const [dimsFoto, setDimsFoto] = useState<{ w: number; h: number } | null>(null)
  // Giro elegido en ESTA sesión de edición. Antes cada click en girar guardaba
  // de inmediato en el backend pero la foto grande de acá abajo seguía
  // mostrándose sin girar (solo se actualizaba la miniatura de arriba): parecía
  // que girar no hacía nada, y si después se dibujaba un recorte, se aplicaba
  // sobre la foto SIN girar (se perdía el giro). Ahora el giro es local: se ve
  // al instante en la foto grande, y "Guardar" manda recorte + giro juntos.
  const [giro, setGiro] = useState<Giro>(0)
  // Hay un cambio sin guardar (giro y/o recuadro): mientras tanto la vista
  // previa deja de mostrar "cómo sale hoy" y pasa a seguir la edición en vivo.
  const editando = giro !== 0 || recuadro !== null

  useEffect(() => {
    if (!editando) return
    dibujarPrevia(previaRef.current, imgRef.current, dimsFoto, giro, recuadro)
  }, [editando, giro, recuadro, dimsFoto])

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

  // Click en el fondo (fuera del recuadro ya dibujado): empieza uno nuevo
  // desde cero, reemplazando al anterior.
  const empezarNuevo = (e: ReactPointerEvent) => {
    const p = posicion(e)
    if (!p) return
    contenedor.current?.setPointerCapture(e.pointerId)
    modo.current = { tipo: 'nuevo' }
    inicio.current = p
    setRecuadro({ x0: p.x, y0: p.y, x1: p.x, y1: p.y })
  }

  // Click DENTRO del recuadro: lo mueve entero, sin cambiar su tamaño.
  const empezarMover = (e: ReactPointerEvent) => {
    if (!recuadro) return
    const p = posicion(e)
    if (!p) return
    e.stopPropagation()
    contenedor.current?.setPointerCapture(e.pointerId)
    modo.current = { tipo: 'mover', dx: p.x - recuadro.x0, dy: p.y - recuadro.y0 }
  }

  // Click en una manija de esquina: agranda/achica arrastrando esa esquina,
  // con la esquina OPUESTA fija como ancla.
  const empezarEsquina = (
    e: ReactPointerEvent,
    esquina: 'x0y0' | 'x1y0' | 'x1y1' | 'x0y1',
  ) => {
    if (!recuadro) return
    e.stopPropagation()
    contenedor.current?.setPointerCapture(e.pointerId)
    const ancla = {
      x0y0: { x: recuadro.x1, y: recuadro.y1 },
      x1y0: { x: recuadro.x0, y: recuadro.y1 },
      x1y1: { x: recuadro.x0, y: recuadro.y0 },
      x0y1: { x: recuadro.x1, y: recuadro.y0 },
    }[esquina]
    modo.current = { tipo: 'esquina', anclaX: ancla.x, anclaY: ancla.y }
  }

  const mover = (e: ReactPointerEvent) => {
    const m = modo.current
    if (!m) return
    const p = posicion(e)
    if (!p) return
    if (m.tipo === 'nuevo') {
      if (!inicio.current) return
      setRecuadro({
        x0: Math.min(inicio.current.x, p.x),
        y0: Math.min(inicio.current.y, p.y),
        x1: Math.max(inicio.current.x, p.x),
        y1: Math.max(inicio.current.y, p.y),
      })
    } else if (m.tipo === 'mover') {
      setRecuadro((r) => {
        if (!r) return r
        const ancho = r.x1 - r.x0
        const alto = r.y1 - r.y0
        const x0 = limitar(Math.min(p.x - m.dx, 1 - ancho))
        const y0 = limitar(Math.min(p.y - m.dy, 1 - alto))
        return { x0, y0, x1: x0 + ancho, y1: y0 + alto }
      })
    } else {
      setRecuadro({
        x0: Math.min(m.anclaX, p.x),
        y0: Math.min(m.anclaY, p.y),
        x1: Math.max(m.anclaX, p.x),
        y1: Math.max(m.anclaY, p.y),
      })
    }
  }

  const terminar = () => {
    modo.current = null
    inicio.current = null
  }

  // Gira la VISTA (no llama al backend): el guardado real pasa por "Guardar".
  // El recuadro ya dibujado se recalcula a la nueva orientación en vez de
  // borrarse: girar no debería obligar a recortar de nuevo desde cero.
  const girar = (delta: 90 | -90) => {
    const nuevo = (((giro + delta) % 360 + 360) % 360) as Giro
    setGiro(nuevo)
    setRecuadro((r) => (r ? recuadroTrasGirar(r, giro, nuevo) : null))
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

        {(recorteActual || editando) && (
          <div
            className="mb-3 flex items-center gap-3 rounded-lg p-2"
            style={{ backgroundColor: 'var(--yuda-primary-soft)' }}
          >
            {editando ? (
              <canvas
                ref={previaRef}
                width={LADO_PREVIA}
                height={LADO_PREVIA}
                style={{ width: 112, height: 112 }}
                className="flex-shrink-0 rounded-lg bg-white"
              />
            ) : (
              <img
                src={recorteActual!}
                alt=""
                style={{ width: 112, height: 112 }}
                className="flex-shrink-0 rounded-lg object-contain"
              />
            )}
            <span className="text-sm" style={{ color: 'var(--yuda-accent)' }}>
              {editando ? t('recorte.previaCambio') : t('recorte.actual')}
            </span>
          </div>
        )}

        <div
          ref={contenedor}
          onPointerDown={empezarNuevo}
          onPointerMove={mover}
          onPointerUp={terminar}
          onPointerCancel={terminar}
          className="relative select-none overflow-hidden rounded-lg"
          style={{ touchAction: 'none', cursor: 'crosshair', backgroundColor: '#111', height: '58vh' }}
        >
          <img
            ref={imgRef}
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
              {/* El recuadro en sí: arrastrarlo desde adentro lo mueve entero,
                  sin cambiar su tamaño. */}
              <div
                onPointerDown={empezarMover}
                className="absolute"
                style={{
                  left: `${recuadroEnPantalla.x0 * 100}%`,
                  top: `${recuadroEnPantalla.y0 * 100}%`,
                  width: `${(recuadroEnPantalla.x1 - recuadroEnPantalla.x0) * 100}%`,
                  height: `${(recuadroEnPantalla.y1 - recuadroEnPantalla.y0) * 100}%`,
                  border: '2px solid var(--yuda-primary)',
                  boxShadow: '0 0 0 9999px rgba(0,0,0,0)',
                  touchAction: 'none',
                  cursor: 'move',
                }}
              />
              {/* Manijas en las 4 esquinas: agrandan o achican el recuadro
                  arrastrando esa esquina, con la opuesta fija. Antes solo se
                  podía volver a dibujar el recuadro entero desde cero. */}
              {(
                [
                  ['x0y0', recuadroEnPantalla.x0, recuadroEnPantalla.y0, 'nwse-resize'],
                  ['x1y0', recuadroEnPantalla.x1, recuadroEnPantalla.y0, 'nesw-resize'],
                  ['x1y1', recuadroEnPantalla.x1, recuadroEnPantalla.y1, 'nwse-resize'],
                  ['x0y1', recuadroEnPantalla.x0, recuadroEnPantalla.y1, 'nesw-resize'],
                ] as const
              ).map(([esquina, left, top, cursor]) => (
                <div
                  key={esquina}
                  onPointerDown={(e) => empezarEsquina(e, esquina)}
                  className="absolute rounded-full border-2 bg-white"
                  style={{
                    left: `${left * 100}%`,
                    top: `${top * 100}%`,
                    width: 22,
                    height: 22,
                    transform: 'translate(-50%, -50%)',
                    borderColor: 'var(--yuda-primary)',
                    touchAction: 'none',
                    cursor,
                  }}
                />
              ))}
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
