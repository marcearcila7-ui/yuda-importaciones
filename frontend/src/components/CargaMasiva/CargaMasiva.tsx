import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { CheckCircle2, ChevronDown, ChevronUp, Image as ImageIcon, Images, Maximize2, Plus, RefreshCw, Sparkles, Trash2, Upload, X } from 'lucide-react'
import { usePackingStore } from '../../store/packingStore'
import { useLoteStore } from '../../store/loteStore'
import { confirmar } from '../../store/confirmStore'
import { ACCEPT_IMAGENES } from '../../lib/imagenes'
import { evaluarLegibilidad } from '../../lib/legibilidad'
import AlertaNoLegible from '../AlertaNoLegible/AlertaNoLegible'
import AvisoDosMinimos from '../AvisoDosMinimos/AvisoDosMinimos'
import type { OCRResultado } from '../../types/ocr'
import type { ItemCreate } from '../../types/packing'

const MAX_LOTE = 100

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-2 py-1 focus:border-[var(--yuda-primary)] focus:outline-none'

// Campo con etiqueta VISIBLE siempre (no placeholder que desaparece al llenarse),
// para que se sepa qué dato es cada uno.
function CampoLote({
  label,
  valor,
  tipo = 'text',
  onChange,
  ancho,
  requerido,
  alerta,
}: {
  label: string
  valor: string | number | null | undefined
  tipo?: 'text' | 'number'
  onChange: (v: string) => void
  ancho?: string
  // requerido = dato obligatorio para poder procesar la foto
  requerido?: boolean
  // alerta = obligatorio y todavía vacío (se resalta en rojo)
  alerta?: boolean
}) {
  return (
    <label className={`flex flex-col gap-0.5 text-xs ${ancho ?? ''}`} style={{ color: 'var(--yuda-text)' }}>
      <span className="font-medium">
        {label}
        {requerido && <span style={{ color: 'var(--yuda-error)' }}> *</span>}
      </span>
      <input
        type={tipo}
        value={valor ?? ''}
        onChange={(e) => onChange(e.target.value)}
        style={{ ...inputStyle, borderColor: alerta ? 'var(--yuda-error)' : undefined }}
        className={inputClase}
      />
    </label>
  )
}

// Las vendedoras se perdian dentro del bloque de carga: no sabian en que momento
// del proceso estaban, cuanto faltaba, ni que iba a pasar despues de cada boton.
// Antes esto tenia ademas su propia barra de "Paso 1/2/3" (BarraPasos compacta),
// pero competia con la barra grande del asistente de arriba (Dashboard.tsx), que
// ya muestra "Fotos" como su paso 1: dos numeradores de "paso 1" a la vez
// confundian mas de lo que ayudaban. Se dejo solo este texto.

function chipConfianza(c: OCRResultado['confianza'], t: (k: string) => string) {
  if (c === 'alta') return { style: { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }, texto: t('ocr.confianzaAlta') }
  if (c === 'media') return { style: { backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }, texto: t('ocr.confianzaMedia') }
  return { style: { backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }, texto: t('ocr.confianzaBaja') }
}

// El bloque de carga es alto: cuando termina el análisis o se agregan los
// productos, se vacía de golpe y la página se acorta. El navegador conserva la
// posición del scroll, que entonces cae al final y obliga a subir a mano. Por eso
// después de cada paso llevamos la vista a la sección que la vendedora necesita ver.
function irASeccion(id: string) {
  // En el siguiente frame: el navegador ya repintó con el alto nuevo.
  requestAnimationFrame(() => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

function CargaMasiva({ onTerminado }: { onTerminado?: () => void }) {
  const { t } = useTranslation()
  const sesionActual = usePackingStore((s) => s.sesionActual)
  const agregarItem = usePackingStore((s) => s.agregarItem)
  const items = usePackingStore((s) => s.items)
  const {
    fase,
    seleccionadas,
    subidas,
    totalSubir,
    procesadas,
    totalProc,
    resultados,
    errores,
    erroresSubida,
    causaSubida,
    falloSistema,
    motivoFallo,
    sinProcesar,
    agregarSeleccion,
    quitarSeleccion,
    cancelarSeleccion,
    procesarSeleccion,
    agregarMas,
    retomar,
    reintentar,
    reanalizarUno,
    reemplazarUno,
    actualizarDato,
    quitar,
    finalizar,
  } = useLoteStore()
  const inputRef = useRef<HTMLInputElement>(null)
  const inputMasRef = useRef<HTMLInputElement>(null)
  const inputReemplazarRef = useRef<HTMLInputElement>(null)

  const [agregando, setAgregando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  // Foto ampliada (lightbox) y tarjeta ocupada (reanálisis/reemplazo en curso)
  const [zoom, setZoom] = useState<string | null>(null)
  const [ocupadoId, setOcupadoId] = useState<string | null>(null)
  const [reemplazarId, setReemplazarId] = useState<string | null>(null)
  // Fotos con el detalle completo desplegado (para revisar/editar todos los datos).
  // Fotos que el navegador no pudo dibujar (las HEIC del iPhone, sobre todo)
  const [sinVista, setSinVista] = useState<Set<string>>(new Set())
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set())
  const toggleExpandido = (id: string) =>
    setExpandidos((s) => {
      const n = new Set(s)
      n.has(id) ? n.delete(id) : n.add(id)
      return n
    })
  const sesionId = sesionActual?.id

  // Al entrar, retomar un lote en curso de esta sesión (si la vendedora cerró y volvió)
  useEffect(() => {
    if (sesionId) retomar(sesionId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionId])

  // Fotos elegidas o a mitad de subir que todavía NO llegaron al servidor: si son
  // tomadas con la cámara del celular (no de la galería), viven solo en la memoria
  // de la pestaña, iOS no las guarda en el rollo de fotos. Recargar por impaciencia
  // ante una subida lenta las perdía sin ningún aviso. Esto no cubre que el
  // sistema operativo mate la pestaña sola por poca memoria o al bloquear el
  // celular (ver retomar() en loteStore, que sí recupera las que ya alcanzaron a
  // subir), solo el caso de recargar o cerrar a propósito.
  useEffect(() => {
    if (fase !== 'seleccion' && fase !== 'subiendo') return
    const avisar = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', avisar)
    return () => window.removeEventListener('beforeunload', avisar)
  }, [fase])

  // Cuando el análisis termina, la barra de progreso (que la vendedora estaba
  // mirando abajo) se reemplaza por la lista de resultados: se lleva la vista al
  // principio del bloque para que empiece a revisarlos desde el primero.
  const faseAnterior = useRef(fase)
  useEffect(() => {
    if (faseAnterior.current === 'procesando' && fase === 'completado') {
      irASeccion('seccion-carga')
    }
    faseAnterior.current = fase
  }, [fase])

  // Elegir fotos: se AGREGAN a la selección (no se procesan hasta pulsar "Procesar")
  const handleArchivos = (e: ChangeEvent<HTMLInputElement>) => {
    const nuevas = Array.from(e.target.files ?? [])
    e.target.value = ''
    if (nuevas.length === 0 || !sesionId) return
    const cupo = Math.max(0, MAX_LOTE - seleccionadas.length)
    let lote = nuevas
    if (nuevas.length > cupo) {
      setAviso(t('lote.tope', { max: MAX_LOTE }))
      lote = nuevas.slice(0, cupo)
    } else {
      setAviso(null)
    }
    if (lote.length > 0) agregarSeleccion(sesionId, lote)
  }

  // Sumar más fotos a la tanda que ya está en revisión (después de procesar)
  const handleAgregarMas = (e: ChangeEvent<HTMLInputElement>) => {
    const nuevas = Array.from(e.target.files ?? [])
    e.target.value = ''
    if (nuevas.length === 0) return
    const cupo = Math.max(0, MAX_LOTE - (resultados.length + errores))
    let lote = nuevas
    if (nuevas.length > cupo) {
      setAviso(t('lote.tope', { max: MAX_LOTE }))
      lote = nuevas.slice(0, cupo)
    } else {
      setAviso(null)
    }
    if (lote.length > 0) agregarMas(lote)
  }

  const actualizarTexto = (id: string, campo: keyof OCRResultado, valor: string) =>
    actualizarDato(id, campo, valor === '' ? null : valor)

  const actualizarNumero = (id: string, campo: keyof OCRResultado, valor: string) => {
    const n = valor === '' ? null : Number(valor)
    actualizarDato(id, campo, n !== null && Number.isNaN(n) ? null : n)
  }

  // Reintento con IA sobre la misma foto de una tarjeta.
  const handleReintentarIA = async (id: string) => {
    setOcupadoId(id)
    try {
      await reanalizarUno(id)
    } catch {
      toast.error(t('lote.errorReanalizar'))
    } finally {
      setOcupadoId(null)
    }
  }

  // Reemplazar la foto de una tarjeta: abre el selector y, al elegir, reanaliza.
  const pedirReemplazo = (id: string) => {
    setReemplazarId(id)
    inputReemplazarRef.current?.click()
  }
  const handleReemplazo = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    const id = reemplazarId
    setReemplazarId(null)
    if (!file || !id) return
    setOcupadoId(id)
    try {
      await reemplazarUno(id, file)
    } catch {
      toast.error(t('lote.errorReanalizar'))
    } finally {
      setOcupadoId(null)
    }
  }

  // Solo los productos con foto legible y datos completos se pueden agregar.
  const legibles = resultados.filter((r) => evaluarLegibilidad(r.datos).ok)
  const noLegibles = resultados.length - legibles.length

  // Agrega los que ya están listos y DEJA en pantalla los que faltan corregir.
  const agregarBuenos = async () => {
    if (legibles.length === 0) return
    setAgregando(true)
    const n = legibles.length
    for (const r of legibles) {
      const d = r.datos
      const item: ItemCreate = {
        supplier_nombre: d.supplier_nombre ?? undefined,
        supplier_numero: d.supplier_numero ?? undefined,
        foto_url: r.foto_url,
        // El recorte automatico al producto: es lo que se incrusta en los
        // documentos. Si no se pudo recortar, queda vacio y se usa la foto entera.
        foto_final_url: r.datos.foto_recorte_url ?? undefined,
        descripcion_es: d.descripcion_es ?? undefined,
        descripcion_en: d.descripcion_en ?? undefined,
        descripcion_zh: d.descripcion_zh ?? undefined,
        material: d.material ?? undefined,
        uso: d.uso ?? undefined,
        qty_por_ctn: d.qty_por_ctn ?? 1,
        price_rmb: d.price_rmb ?? 0,
        gw: 0,
        largo_cm: d.largo_cm ?? 0,
        ancho_cm: d.ancho_cm ?? 0,
        alto_cm: d.alto_cm ?? 0,
        cbm: d.cbm_directo ?? undefined,
        moq_cajas: d.cantidad_minima ?? undefined,
        ctns: 1,
      }
      await agregarItem(item)
      quitar(r.id)
    }
    const quedan = resultados.length - n
    setAgregando(false)
    if (quedan <= 0) {
      await finalizar()
      toast.success(t('lote.exitoFinal', { n }))
      // Ya no queda nada por corregir: este paso terminó y se pasa al siguiente.
      onTerminado?.()
    } else {
      toast.success(t('lote.exitoParcial', { n, quedan }))
      // Quedan fotos por corregir: se vuelve arriba del bloque de carga.
      irASeccion('seccion-carga')
    }
  }

  const enProgreso = fase === 'subiendo' || fase === 'procesando'
  const pct =
    fase === 'subiendo'
      ? totalSubir
        ? (subidas / totalSubir) * 100
        : 0
      : totalProc
        ? (procesadas / totalProc) * 100
        : 0

  // Cuando ya se agregaron TODOS los productos de una tanda, el lote se cierra y
  // esta pantalla vuelve a quedar vacía (correcto: ya no hay nada pendiente que
  // revisar acá). Pero para la vendedora, volver a ver el botón de "Seleccionar
  // fotos" vacío daba la impresión de que sus fotos habían desaparecido, cuando en
  // realidad ya están en Productos convertidas en ítems. Se lo aclara acá.
  const ayudaPaso =
    fase === 'idle'
      ? items.length > 0
        ? t('lote.ayudaPaso1ConProductos', { n: items.length })
        : t('lote.ayudaPaso1', { max: MAX_LOTE })
      : fase === 'seleccion'
        ? t('lote.ayudaPaso1Elegidas')
        : enProgreso
          ? t('lote.ayudaPaso2')
          : t('lote.ayudaPaso3')

  return (
    <div className="flex w-full flex-col gap-4">
      <p
        className="rounded-lg px-3 py-2 text-sm"
        style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-accent)' }}
      >
        {ayudaPaso}
      </p>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_IMAGENES}
        multiple
        onChange={handleArchivos}
        className="hidden"
      />
      <input
        ref={inputMasRef}
        type="file"
        accept={ACCEPT_IMAGENES}
        multiple
        onChange={handleAgregarMas}
        className="hidden"
      />

      {/* Paso 1: elegir las primeras fotos */}
      {fase === 'idle' && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white"
          style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 16 }}
        >
          <Images size={18} /> {t('lote.seleccionar')}
        </button>
      )}

      {aviso && <p className="text-sm" style={{ color: 'var(--yuda-warning-dark)' }}>{aviso}</p>}

      {/* Fotos que no llegaron a subir. El mensaje depende de DE QUIEN fue la culpa:
          si se cayo nuestro almacenamiento, volver a tomarlas no arregla nada. */}
      {erroresSubida > 0 && (
        <div className="rounded-lg px-3 py-2" style={{ backgroundColor: '#FEF2F2', color: 'var(--yuda-error-dark)' }}>
          <p className="text-sm font-semibold">
            {t(causaSubida === 'servidor' ? 'lote.fallidasSubidaSistemaTitulo' : 'lote.fallidasSubidaTitulo', { n: erroresSubida })}
          </p>
          <p className="mt-1 text-sm">
            {t(causaSubida === 'servidor' ? 'lote.fallidasSubidaSistemaTexto' : 'lote.fallidasSubidaTexto')}
          </p>
        </div>
      )}

      {/* Paso 2: selección en curso — armar la tanda y luego procesar */}
      {fase === 'seleccion' && (
        <div className="flex flex-col gap-4">
          <p className="text-sm font-medium" style={{ color: 'var(--yuda-accent)' }}>
            {t('lote.listas', { n: seleccionadas.length })}
          </p>

          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4">
            {seleccionadas.map((f) => (
              <div
                key={f.id}
                className="relative aspect-square overflow-hidden rounded-xl border"
                style={{ borderColor: 'var(--yuda-border)' }}
              >
                {sinVista.has(f.id) ? (
                  // Las fotos de iPhone (HEIC) el navegador no las sabe dibujar, asi
                  // que la miniatura salia como imagen rota. Se suben igual y el
                  // backend las convierte: aca solo hay que decirlo en vez de
                  // mostrar un icono roto que parece un error.
                  <div className="flex h-full w-full flex-col items-center justify-center gap-1 p-2 text-center" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
                    <ImageIcon size={22} style={{ color: 'var(--yuda-primary)' }} />
                    <span className="w-full truncate text-xs font-medium" style={{ color: 'var(--yuda-accent)' }}>
                      {f.file.name}
                    </span>
                    <span className="text-xs leading-tight" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {t('lote.sinVistaPrevia')}
                    </span>
                  </div>
                ) : (
                  <img
                    src={f.preview}
                    alt=""
                    className="h-full w-full object-cover"
                    onError={() => setSinVista((s) => new Set(s).add(f.id))}
                  />
                )}
                <button
                  type="button"
                  onClick={() => quitarSeleccion(f.id)}
                  aria-label={t('lote.quitar')}
                  className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full text-white"
                  style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}
                >
                  <X size={14} />
                </button>
              </div>
            ))}

            {/* Tile "+" para agregar más fotos a la selección */}
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className="flex aspect-square flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed"
              style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)' }}
            >
              <Plus size={24} />
              <span className="text-xs font-semibold">{t('lote.agregar')}</span>
            </button>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              onClick={procesarSeleccion}
              disabled={seleccionadas.length === 0}
              className="flex min-h-[52px] flex-1 items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 16 }}
            >
              <Sparkles size={18} /> {t('lote.procesar', { n: seleccionadas.length })}
            </button>
            <button
              type="button"
              onClick={cancelarSeleccion}
              className="min-h-[52px] rounded-lg font-medium sm:px-6"
              style={{ color: 'var(--yuda-text-secondary)' }}
            >
              {t('lote.descartar')}
            </button>
          </div>
        </div>
      )}

      {/* Progreso (subiendo o procesando). La barra pasaba de subir al 100% a
          "reiniciar" en 0% para leer las etiquetas, y sin nada que lo explicara
          parecía que se había colgado o vuelto a empezar. Esta línea con el visto
          queda fija al pasar a "procesando" para que se vea que subir SÍ terminó
          bien y lo que sigue es un paso nuevo, no un reinicio. */}
      {enProgreso && (
        <div>
          {fase === 'procesando' && (
            <p className="mb-2 flex items-center gap-1 text-xs font-semibold" style={{ color: 'var(--yuda-success)' }}>
              <CheckCircle2 size={14} /> {t('lote.fotosSubidasListo', { n: totalSubir })}
            </p>
          )}
          <p className="mb-2 text-sm font-medium" style={{ color: 'var(--yuda-accent)' }}>
            {fase === 'subiendo'
              ? t('lote.subiendo', { hechas: subidas, total: totalSubir })
              : t('lote.procesando', { hechas: procesadas, total: totalProc })}
          </p>
          <div className="h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
            <div className="h-full transition-all" style={{ width: `${pct}%`, backgroundColor: 'var(--yuda-primary)' }} />
          </div>
          {fase === 'procesando' && (
            <p className="mt-2 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('lote.segundoPlano')}
            </p>
          )}
        </div>
      )}

      {/* Fotos que fallaron (con reintento) */}
      {fase === 'completado' && (errores > 0 || falloSistema) && (
        <div className="rounded-xl p-3" style={{ backgroundColor: 'var(--yuda-error-soft)' }}>
          {falloSistema ? (
            // El problema es del sistema (API caida o sin credito): decirlo claro.
            // Las fotos ya estan guardadas, no hay que volver a tomarlas.
            <div className="mb-2">
              <p className="text-sm font-semibold" style={{ color: 'var(--yuda-error)' }}>
                {t(motivoFallo === 'sin_saldo' ? 'lote.falloSaldoTitulo' : 'lote.falloSistemaTitulo')}
              </p>
              <p className="mt-1 text-sm" style={{ color: 'var(--yuda-error)' }}>
                {motivoFallo === 'sin_saldo'
                  ? t('lote.falloSaldoTexto')
                  : sinProcesar > 0
                    ? t('lote.falloSistemaTextoCortado', { n: sinProcesar })
                    : t('lote.falloSistemaTexto')}
              </p>
              {sinProcesar > 0 && (
                <p className="mt-1 text-sm" style={{ color: 'var(--yuda-error)' }}>
                  {t('lote.falloFotosGuardadas', { n: sinProcesar })}
                </p>
              )}
            </div>
          ) : (
            <p className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-error)' }}>
              {t('lote.fallidasTitulo', { n: errores })}
            </p>
          )}
          <button
            type="button"
            onClick={reintentar}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white"
            style={{ backgroundColor: 'var(--yuda-error)' }}
          >
            <RefreshCw size={16} /> {t('lote.reintentar')}
          </button>
        </div>
      )}

      {/* Revisión en bloque */}
      {fase === 'completado' && resultados.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div>
              <h3 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
                {t('lote.revisar', { n: resultados.length })}
              </h3>
              <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>{t('ocr.revisarAyuda')}</p>
            </div>
            <button
              type="button"
              onClick={async () => {
                const ok = await confirmar({
                  mensaje: t('lote.confirmarDescartar', { n: resultados.length }),
                  peligro: true,
                  textoConfirmar: t('lote.descartar'),
                })
                if (ok) finalizar()
              }}
              className="text-sm font-medium"
              style={{ color: 'var(--yuda-text-secondary)' }}
            >
              {t('lote.descartar')}
            </button>
          </div>

          <div
            className="rounded-lg px-3 py-2 text-sm font-medium"
            style={
              noLegibles > 0
                ? { backgroundColor: '#FEF2F2', color: 'var(--yuda-error-dark)' }
                : { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
            }
          >
            {noLegibles > 0
              ? t('lote.resumenPendientes', { listos: legibles.length, pendientes: noLegibles })
              : t('lote.resumenTodoListo', { n: legibles.length })}
          </div>

          {resultados.map((r) => {
            const chip = chipConfianza(r.datos.confianza, t)
            const legibilidad = evaluarLegibilidad(r.datos)
            const faltaSet = new Set(legibilidad.faltantes)
            const ocupado = ocupadoId === r.id
            return (
              <div
                key={r.id}
                className="flex flex-col gap-3 rounded-xl border p-3"
                style={{ borderColor: legibilidad.ok ? 'var(--yuda-border)' : '#FCA5A5' }}
              >
              {/* Fila: foto grande (ampliable) + confianza + quitar */}
              <div className="flex items-start gap-3">
                {r.foto_url ? (
                  <button
                    type="button"
                    onClick={() => setZoom(r.foto_url)}
                    className="relative flex-shrink-0 overflow-hidden rounded-lg"
                    style={{ width: 104, height: 104 }}
                    aria-label={t('lote.ampliar')}
                  >
                    <img src={r.foto_url} alt="" className="h-full w-full object-cover" />
                    <span className="absolute bottom-1 right-1 flex h-6 w-6 items-center justify-center rounded-full text-white" style={{ backgroundColor: 'rgba(0,0,0,0.55)' }}>
                      <Maximize2 size={13} />
                    </span>
                  </button>
                ) : (
                  <div style={{ width: 104, height: 104 }} className="flex-shrink-0 rounded-lg bg-gray-100" />
                )}
                <div className="flex flex-1 flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chip.style}>
                      {chip.texto}
                    </span>
                    <button type="button" onClick={() => quitar(r.id)} aria-label={t('lote.quitar')} className="ml-auto" style={{ color: 'var(--yuda-error)' }}>
                      <Trash2 size={18} />
                    </button>
                  </div>
                  {!legibilidad.ok && (
                    <p className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {t('lote.completaOReemplaza')}
                    </p>
                  )}
                </div>
              </div>

              {/* Datos que la foto necesita para poder procesarse (* = obligatorio) */}
              <div className="grid grid-cols-2 gap-2">
                <CampoLote ancho="col-span-2" label={t('ocr.proveedor')} valor={r.datos.supplier_nombre} requerido alerta={faltaSet.has('proveedor')}
                  onChange={(v) => actualizarTexto(r.id, 'supplier_nombre', v)} />
                <CampoLote ancho="col-span-2" label={t('packing.fDescripcion')} valor={r.datos.descripcion_es}
                  onChange={(v) => actualizarTexto(r.id, 'descripcion_es', v)} />
                <CampoLote label={t('ocr.precioRMB')} valor={r.datos.price_rmb} tipo="number" requerido alerta={faltaSet.has('precioRMB')}
                  onChange={(v) => actualizarNumero(r.id, 'price_rmb', v)} />
                <CampoLote label={t('ocr.unidPorCaja')} valor={r.datos.qty_por_ctn} tipo="number" requerido alerta={faltaSet.has('unidPorCaja')}
                  onChange={(v) => actualizarNumero(r.id, 'qty_por_ctn', v)} />
                <div>
                  <CampoLote label={t('ocr.mqt')} valor={r.datos.cantidad_minima} tipo="number" requerido alerta={faltaSet.has('mqt')}
                    onChange={(v) => actualizarNumero(r.id, 'cantidad_minima', v)} />
                  <AvisoDosMinimos
                    actual={r.datos.cantidad_minima}
                    tienda={r.datos.cantidad_minima_tienda}
                    onElegir={(v) => actualizarNumero(r.id, 'cantidad_minima', String(v))}
                  />
                </div>
                <CampoLote label={t('ocr.cbm')} valor={r.datos.cbm_directo} tipo="number" requerido alerta={faltaSet.has('cbm')}
                  onChange={(v) => actualizarNumero(r.id, 'cbm_directo', v)} />
              </div>

              <button
                type="button"
                onClick={() => toggleExpandido(r.id)}
                className="flex items-center gap-1 self-start text-xs font-semibold"
                style={{ color: 'var(--yuda-primary)' }}
              >
                {expandidos.has(r.id) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                {expandidos.has(r.id) ? t('ocr.verMenos') : t('ocr.verMas')}
              </button>

              {expandidos.has(r.id) && (
                <div className="grid grid-cols-2 gap-2 rounded-lg bg-white p-2">
                  <CampoLote label={t('ocr.nStand')} valor={r.datos.supplier_numero}
                    onChange={(v) => actualizarTexto(r.id, 'supplier_numero', v)} />
                  <CampoLote label={t('ocr.colores')} valor={r.datos.colores}
                    onChange={(v) => actualizarTexto(r.id, 'colores', v)} />
                  <CampoLote ancho="col-span-2" label={t('ocr.descripcionEn')} valor={r.datos.descripcion_en}
                    onChange={(v) => actualizarTexto(r.id, 'descripcion_en', v)} />
                  <CampoLote ancho="col-span-2" label={t('ocr.descripcionZh')} valor={r.datos.descripcion_zh}
                    onChange={(v) => actualizarTexto(r.id, 'descripcion_zh', v)} />
                  <CampoLote label={t('ocr.material')} valor={r.datos.material}
                    onChange={(v) => actualizarTexto(r.id, 'material', v)} />
                  <CampoLote label={t('ocr.uso')} valor={r.datos.uso}
                    onChange={(v) => actualizarTexto(r.id, 'uso', v)} />
                  <CampoLote label={t('ocr.largoCm')} valor={r.datos.largo_cm} tipo="number"
                    onChange={(v) => actualizarNumero(r.id, 'largo_cm', v)} />
                  <CampoLote label={t('ocr.anchoCm')} valor={r.datos.ancho_cm} tipo="number"
                    onChange={(v) => actualizarNumero(r.id, 'ancho_cm', v)} />
                  <CampoLote label={t('ocr.altoCm')} valor={r.datos.alto_cm} tipo="number"
                    onChange={(v) => actualizarNumero(r.id, 'alto_cm', v)} />
                </div>
              )}

              {!legibilidad.ok && <AlertaNoLegible legibilidad={legibilidad} compacta />}

              {/* Acciones IA para las fotos que fallaron: reintentar o reemplazar */}
              {!legibilidad.ok && (
                <div className="flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => handleReintentarIA(r.id)}
                    disabled={ocupado}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: 'var(--yuda-primary)' }}
                  >
                    <Sparkles size={16} /> {ocupado ? t('lote.analizando') : t('lote.reintentarIA')}
                  </button>
                  <button
                    type="button"
                    onClick={() => pedirReemplazo(r.id)}
                    disabled={ocupado}
                    className="flex flex-1 items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold disabled:opacity-60"
                    style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)' }}
                  >
                    <Upload size={16} /> {t('lote.reemplazarFoto')}
                  </button>
                </div>
              )}
              </div>
            )
          })}

          <button
            type="button"
            onClick={() => inputMasRef.current?.click()}
            disabled={agregando}
            className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg font-semibold disabled:opacity-60"
            style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)', fontSize: 16 }}
          >
            <Images size={18} /> {t('lote.agregarMas')}
          </button>

          <button
            type="button"
            onClick={agregarBuenos}
            disabled={agregando || legibles.length === 0}
            className="min-h-[52px] w-full rounded-lg font-semibold text-white disabled:opacity-60"
            style={{ backgroundColor: 'var(--yuda-success)', fontSize: 16 }}
          >
            {agregando ? t('lote.agregando') : t('lote.agregarListos', { n: legibles.length })}
          </button>
        </div>
      )}

      {/* Input oculto para reemplazar la foto de una tarjeta */}
      <input
        ref={inputReemplazarRef}
        type="file"
        accept={ACCEPT_IMAGENES}
        onChange={handleReemplazo}
        className="hidden"
      />

      {/* Lightbox: foto ampliada al tocar */}
      {zoom && (
        <div
          onClick={() => setZoom(null)}
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ backgroundColor: 'rgba(0,0,0,0.8)' }}
          role="dialog"
        >
          <img src={zoom} alt="" style={{ maxWidth: '100%', maxHeight: '100%' }} className="rounded-lg" />
          <button
            type="button"
            onClick={() => setZoom(null)}
            aria-label={t('lote.cerrar')}
            className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full text-white"
            style={{ backgroundColor: 'rgba(0,0,0,0.6)' }}
          >
            <X size={20} />
          </button>
        </div>
      )}
    </div>
  )
}

export default CargaMasiva
