import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Images, RefreshCw, Trash2 } from 'lucide-react'
import { usePackingStore } from '../../store/packingStore'
import { useLoteStore } from '../../store/loteStore'
import { evaluarLegibilidad } from '../../lib/legibilidad'
import AlertaNoLegible from '../AlertaNoLegible/AlertaNoLegible'
import type { OCRResultado } from '../../types/ocr'
import type { ItemCreate } from '../../types/packing'

const MAX_LOTE = 100

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-2 py-1 focus:border-[#4B52E8] focus:outline-none'

function chipConfianza(c: OCRResultado['confianza'], t: (k: string) => string) {
  if (c === 'alta') return { style: { backgroundColor: '#D1FAE5', color: '#10B981' }, texto: t('ocr.confianzaAlta') }
  if (c === 'media') return { style: { backgroundColor: '#FEF3C7', color: '#B45309' }, texto: t('ocr.confianzaMedia') }
  return { style: { backgroundColor: '#FEE2E2', color: '#EF4444' }, texto: t('ocr.confianzaBaja') }
}

function CargaMasiva() {
  const { t } = useTranslation()
  const sesionActual = usePackingStore((s) => s.sesionActual)
  const agregarItem = usePackingStore((s) => s.agregarItem)
  const {
    fase,
    subidas,
    totalSubir,
    procesadas,
    totalProc,
    resultados,
    errores,
    iniciar,
    agregarMas,
    retomar,
    reintentar,
    actualizarDato,
    quitar,
    finalizar,
  } = useLoteStore()
  const inputRef = useRef<HTMLInputElement>(null)
  const inputMasRef = useRef<HTMLInputElement>(null)

  const [agregando, setAgregando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)
  const sesionId = sesionActual?.id

  // Al entrar, retomar un lote en curso de esta sesión (si la vendedora cerró y volvió)
  useEffect(() => {
    if (sesionId) retomar(sesionId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesionId])

  const handleSeleccion = (e: ChangeEvent<HTMLInputElement>) => {
    const todos = Array.from(e.target.files ?? [])
    e.target.value = ''
    if (todos.length === 0 || !sesionId) return
    let lote = todos
    if (todos.length > MAX_LOTE) {
      setAviso(t('lote.tope', { max: MAX_LOTE }))
      lote = todos.slice(0, MAX_LOTE)
    } else {
      setAviso(null)
    }
    iniciar(sesionId, lote)
  }

  // Sumar más fotos a la tanda que ya está en revisión
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

  // Solo los productos con foto legible y datos completos se pueden agregar.
  const legibles = resultados.filter((r) => evaluarLegibilidad(r.datos).ok)
  const noLegibles = resultados.length - legibles.length

  const agregarTodos = async () => {
    if (legibles.length === 0) return
    setAgregando(true)
    const n = legibles.length
    for (const r of legibles) {
      const d = r.datos
      const item: ItemCreate = {
        supplier_nombre: d.supplier_nombre ?? undefined,
        supplier_numero: d.supplier_numero ?? undefined,
        foto_url: r.foto_url,
        descripcion_es: d.descripcion_es ?? undefined,
        descripcion_en: d.descripcion_en ?? undefined,
        descripcion_zh: d.descripcion_zh ?? undefined,
        material: d.material ?? undefined,
        uso: d.uso ?? undefined,
        qty_por_ctn: d.qty_por_ctn ?? 1,
        price_rmb: d.price_rmb ?? 0,
        gw: d.gw ?? 0,
        largo_cm: d.largo_cm ?? 0,
        ancho_cm: d.ancho_cm ?? 0,
        alto_cm: d.alto_cm ?? 0,
        cbm: d.cbm_directo ?? undefined,
        moq_cajas: d.cantidad_minima ?? undefined,
        ctns: 1,
      }
      await agregarItem(item)
    }
    await finalizar()
    setAgregando(false)
    toast.success(t('lote.exito', { n }))
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

  return (
    <div className="flex w-full flex-col gap-4">
      <p className="text-sm" style={{ color: '#6B7280' }}>
        {t('lote.instruccion', { max: MAX_LOTE })}
      </p>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        onChange={handleSeleccion}
        className="hidden"
      />
      <input
        ref={inputMasRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        onChange={handleAgregarMas}
        className="hidden"
      />

      {fase === 'idle' && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white"
          style={{ backgroundColor: '#4B52E8', fontSize: 16 }}
        >
          <Images size={18} /> {t('lote.seleccionar')}
        </button>
      )}

      {aviso && <p className="text-sm" style={{ color: '#B45309' }}>{aviso}</p>}

      {/* Progreso (subiendo o procesando) */}
      {enProgreso && (
        <div>
          <p className="mb-2 text-sm font-medium" style={{ color: '#0D0D0D' }}>
            {fase === 'subiendo'
              ? t('lote.subiendo', { hechas: subidas, total: totalSubir })
              : t('lote.procesando', { hechas: procesadas, total: totalProc })}
          </p>
          <div className="h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: '#EEF0FD' }}>
            <div className="h-full transition-all" style={{ width: `${pct}%`, backgroundColor: '#4B52E8' }} />
          </div>
          {fase === 'procesando' && (
            <p className="mt-2 text-xs" style={{ color: '#6B7280' }}>
              {t('lote.segundoPlano')}
            </p>
          )}
        </div>
      )}

      {/* Fotos que fallaron (con reintento) */}
      {fase === 'completado' && errores > 0 && (
        <div className="rounded-xl p-3" style={{ backgroundColor: '#FEE2E2' }}>
          <p className="mb-2 text-sm font-semibold" style={{ color: '#EF4444' }}>
            {t('lote.fallidasTitulo', { n: errores })}
          </p>
          <button
            type="button"
            onClick={reintentar}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-white"
            style={{ backgroundColor: '#EF4444' }}
          >
            <RefreshCw size={16} /> {t('lote.reintentar')}
          </button>
        </div>
      )}

      {/* Revisión en bloque */}
      {fase === 'completado' && resultados.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 style={{ fontWeight: 700, fontSize: 16, color: '#0D0D0D' }}>
              {t('lote.revisar', { n: resultados.length })}
            </h3>
            <button type="button" onClick={finalizar} className="text-sm font-medium" style={{ color: '#6B7280' }}>
              {t('lote.descartar')}
            </button>
          </div>

          {noLegibles > 0 && (
            <p className="rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: '#FEF2F2', color: '#B91C1C' }}>
              {t('lote.noLegibles', { n: noLegibles })}
            </p>
          )}

          {resultados.map((r) => {
            const chip = chipConfianza(r.datos.confianza, t)
            const legibilidad = evaluarLegibilidad(r.datos)
            return (
              <div
                key={r.id}
                className="flex flex-col gap-3 rounded-xl border p-3"
                style={{ borderColor: legibilidad.ok ? '#E5E7EB' : '#FCA5A5' }}
              >
              <div className="flex gap-3">
                {r.foto_url ? (
                  <img src={r.foto_url} alt="" style={{ width: 56, height: 56 }} className="flex-shrink-0 rounded-lg object-cover" />
                ) : (
                  <div style={{ width: 56, height: 56 }} className="flex-shrink-0 rounded-lg bg-gray-100" />
                )}

                <div className="grid flex-1 grid-cols-2 gap-2">
                  <input style={inputStyle} className={`${inputClase} col-span-2`} placeholder={t('ocr.proveedor')}
                    value={(r.datos.supplier_nombre as string | null) ?? ''}
                    onChange={(e) => actualizarTexto(r.id, 'supplier_nombre', e.target.value)} />
                  <input style={inputStyle} className={`${inputClase} col-span-2`} placeholder={t('packing.fDescripcion')}
                    value={(r.datos.descripcion_es as string | null) ?? ''}
                    onChange={(e) => actualizarTexto(r.id, 'descripcion_es', e.target.value)} />
                  <input type="number" style={inputStyle} className={inputClase} placeholder={t('ocr.precioRMB')}
                    value={(r.datos.price_rmb as number | null) ?? ''}
                    onChange={(e) => actualizarNumero(r.id, 'price_rmb', e.target.value)} />
                  <input type="number" style={inputStyle} className={inputClase} placeholder={t('ocr.unidPorCaja')}
                    value={(r.datos.qty_por_ctn as number | null) ?? ''}
                    onChange={(e) => actualizarNumero(r.id, 'qty_por_ctn', e.target.value)} />
                </div>

                <div className="flex flex-shrink-0 flex-col items-end justify-between">
                  <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chip.style}>
                    {chip.texto}
                  </span>
                  <button type="button" onClick={() => quitar(r.id)} aria-label={t('lote.quitar')} style={{ color: '#EF4444' }}>
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>

              {!legibilidad.ok && <AlertaNoLegible legibilidad={legibilidad} compacta />}
              </div>
            )
          })}

          <button
            type="button"
            onClick={() => inputMasRef.current?.click()}
            disabled={agregando}
            className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg font-semibold disabled:opacity-60"
            style={{ backgroundColor: '#EEF0FD', color: '#4B52E8', fontSize: 16 }}
          >
            <Images size={18} /> {t('lote.agregarMas')}
          </button>

          <button
            type="button"
            onClick={agregarTodos}
            disabled={agregando || legibles.length === 0}
            className="min-h-[52px] w-full rounded-lg font-semibold text-white disabled:opacity-60"
            style={{ backgroundColor: '#10B981', fontSize: 16 }}
          >
            {agregando ? t('lote.agregando') : t('lote.agregarTodos', { n: legibles.length })}
          </button>
        </div>
      )}
    </div>
  )
}

export default CargaMasiva
