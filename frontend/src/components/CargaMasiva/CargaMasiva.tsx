import { useRef, useState } from 'react'
import type { ChangeEvent, CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Images, Trash2 } from 'lucide-react'
import { subirFotoOCR } from '../../api/ocr'
import { comprimirImagen } from '../../lib/comprimirImagen'
import { usePackingStore } from '../../store/packingStore'
import type { OCRResultado } from '../../types/ocr'
import type { ItemCreate } from '../../types/packing'

// Tope coherente por tanda y cuántas se leen en paralelo
const MAX_LOTE = 50
const CONCURRENCIA = 4

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-2 py-1 focus:border-[#4B52E8] focus:outline-none'

interface Resultado {
  id: string
  foto_url: string
  datos: OCRResultado
}

function chipConfianza(c: OCRResultado['confianza'], t: (k: string) => string) {
  if (c === 'alta') return { style: { backgroundColor: '#D1FAE5', color: '#10B981' }, texto: t('ocr.confianzaAlta') }
  if (c === 'media') return { style: { backgroundColor: '#FEF3C7', color: '#B45309' }, texto: t('ocr.confianzaMedia') }
  return { style: { backgroundColor: '#FEE2E2', color: '#EF4444' }, texto: t('ocr.confianzaBaja') }
}

function CargaMasiva() {
  const { t } = useTranslation()
  const agregarItem = usePackingStore((s) => s.agregarItem)
  const inputRef = useRef<HTMLInputElement>(null)

  const [procesando, setProcesando] = useState(false)
  const [progreso, setProgreso] = useState({ hechas: 0, total: 0 })
  const [resultados, setResultados] = useState<Resultado[]>([])
  const [agregando, setAgregando] = useState(false)
  const [aviso, setAviso] = useState<string | null>(null)

  const handleSeleccion = async (e: ChangeEvent<HTMLInputElement>) => {
    const todos = Array.from(e.target.files ?? [])
    e.target.value = '' // permite volver a elegir las mismas
    if (todos.length === 0) return

    let lote = todos
    if (todos.length > MAX_LOTE) {
      setAviso(t('lote.tope', { max: MAX_LOTE }))
      lote = todos.slice(0, MAX_LOTE)
    } else {
      setAviso(null)
    }

    setResultados([])
    setProcesando(true)
    setProgreso({ hechas: 0, total: lote.length })

    let fallidas = 0
    const acumulados: Resultado[] = []
    let idx = 0
    const worker = async () => {
      while (idx < lote.length) {
        const archivo = lote[idx++]
        try {
          const comprimido = await comprimirImagen(archivo)
          const resp = await subirFotoOCR(comprimido)
          acumulados.push({ id: resp.foto_url, foto_url: resp.foto_url, datos: { ...resp.datos_extraidos } })
        } catch {
          fallidas++
        }
        setProgreso((p) => ({ ...p, hechas: p.hechas + 1 }))
      }
    }
    await Promise.all(Array.from({ length: Math.min(CONCURRENCIA, lote.length) }, worker))

    setResultados(acumulados)
    setProcesando(false)
    if (fallidas > 0) toast.error(t('lote.fallas', { n: fallidas }))
  }

  const actualizarTexto = (id: string, campo: keyof OCRResultado, valor: string) => {
    setResultados((rs) =>
      rs.map((r) => (r.id === id ? { ...r, datos: { ...r.datos, [campo]: valor === '' ? null : valor } } : r)),
    )
  }

  const actualizarNumero = (id: string, campo: keyof OCRResultado, valor: string) => {
    const n = valor === '' ? null : Number(valor)
    setResultados((rs) =>
      rs.map((r) =>
        r.id === id ? { ...r, datos: { ...r.datos, [campo]: n !== null && Number.isNaN(n) ? null : n } } : r,
      ),
    )
  }

  const quitar = (id: string) => setResultados((rs) => rs.filter((r) => r.id !== id))

  const agregarTodos = async () => {
    if (resultados.length === 0) return
    setAgregando(true)
    const n = resultados.length
    for (const r of resultados) {
      const d = r.datos
      const item: ItemCreate = {
        supplier_nombre: d.supplier_nombre ?? undefined,
        supplier_numero: d.supplier_numero ?? undefined,
        foto_url: r.foto_url,
        descripcion_zh: d.descripcion_zh ?? undefined,
        qty_por_ctn: d.qty_por_ctn ?? 1,
        price_rmb: d.price_rmb ?? 0,
        gw: d.gw ?? 0,
        largo_cm: d.largo_cm ?? 0,
        ancho_cm: d.ancho_cm ?? 0,
        alto_cm: d.alto_cm ?? 0,
        ctns: 1,
      }
      await agregarItem(item)
    }
    setResultados([])
    setAgregando(false)
    toast.success(t('lote.exito', { n }))
  }

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

      {/* Botón seleccionar (oculto mientras hay resultados para revisar) */}
      {resultados.length === 0 && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={procesando}
          className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
          style={{ backgroundColor: '#4B52E8', fontSize: 16 }}
        >
          <Images size={18} /> {t('lote.seleccionar')}
        </button>
      )}

      {aviso && <p className="text-sm" style={{ color: '#B45309' }}>{aviso}</p>}

      {/* Progreso */}
      {procesando && (
        <div>
          <p className="mb-2 text-sm font-medium" style={{ color: '#0D0D0D' }}>
            {t('lote.procesando', { hechas: progreso.hechas, total: progreso.total })}
          </p>
          <div className="h-2 w-full overflow-hidden rounded-full" style={{ backgroundColor: '#EEF0FD' }}>
            <div
              className="h-full transition-all"
              style={{
                width: `${progreso.total ? (progreso.hechas / progreso.total) * 100 : 0}%`,
                backgroundColor: '#4B52E8',
              }}
            />
          </div>
        </div>
      )}

      {/* Revisión en bloque */}
      {resultados.length > 0 && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 style={{ fontWeight: 700, fontSize: 16, color: '#0D0D0D' }}>
              {t('lote.revisar', { n: resultados.length })}
            </h3>
          </div>

          {resultados.map((r) => {
            const chip = chipConfianza(r.datos.confianza, t)
            return (
              <div
                key={r.id}
                className="flex gap-3 rounded-xl border border-gray-200 p-3"
              >
                {r.foto_url ? (
                  <img src={r.foto_url} alt="" style={{ width: 56, height: 56 }} className="flex-shrink-0 rounded-lg object-cover" />
                ) : (
                  <div style={{ width: 56, height: 56 }} className="flex-shrink-0 rounded-lg bg-gray-100" />
                )}

                <div className="grid flex-1 grid-cols-2 gap-2">
                  <input style={inputStyle} className={`${inputClase} col-span-2`} placeholder={t('ocr.proveedor')}
                    value={(r.datos.supplier_nombre as string | null) ?? ''}
                    onChange={(e) => actualizarTexto(r.id, 'supplier_nombre', e.target.value)} />
                  <input style={inputStyle} className={`${inputClase} col-span-2`} placeholder={t('ocr.descripcionZh')}
                    value={(r.datos.descripcion_zh as string | null) ?? ''}
                    onChange={(e) => actualizarTexto(r.id, 'descripcion_zh', e.target.value)} />
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
            )
          })}

          <button
            type="button"
            onClick={agregarTodos}
            disabled={agregando}
            className="min-h-[52px] w-full rounded-lg font-semibold text-white disabled:opacity-60"
            style={{ backgroundColor: '#10B981', fontSize: 16 }}
          >
            {agregando ? t('lote.agregando') : t('lote.agregarTodos', { n: resultados.length })}
          </button>
        </div>
      )}
    </div>
  )
}

export default CargaMasiva
