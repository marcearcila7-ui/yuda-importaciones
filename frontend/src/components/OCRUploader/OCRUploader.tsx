import { useCallback, useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useDropzone } from 'react-dropzone'
import { subirFotoOCR } from '../../api/ocr'
import type { OCRResponse, OCRResultado } from '../../types/ocr'

interface OCRUploaderProps {
  onItemConfirmado: (datos: OCRResultado & { foto_url: string }) => void
}

// Requisitos críticos de mobile
const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none'

// Campos numéricos editables del panel de revisión
const CAMPOS_NUMERO: Array<{ clave: keyof OCRResultado; etiqueta: string }> = [
  { clave: 'price_rmb', etiqueta: 'Precio RMB' },
  { clave: 'qty_por_ctn', etiqueta: 'Unid. por caja' },
  { clave: 'largo_cm', etiqueta: 'Largo cm' },
  { clave: 'ancho_cm', etiqueta: 'Ancho cm' },
  { clave: 'alto_cm', etiqueta: 'Alto cm' },
  { clave: 'gw', etiqueta: 'Peso bruto kg' },
]

// Campos de texto editables del panel de revisión
const CAMPOS_TEXTO: Array<{ clave: keyof OCRResultado; etiqueta: string }> = [
  { clave: 'supplier_nombre', etiqueta: 'Proveedor' },
  { clave: 'supplier_numero', etiqueta: 'N° Stand' },
  { clave: 'colores', etiqueta: 'Colores' },
  { clave: 'descripcion_zh', etiqueta: 'Descripción en chino' },
]

function chipConfianza(confianza: OCRResultado['confianza']): { style: CSSProperties; texto: string } {
  if (confianza === 'alta') return { style: { backgroundColor: '#D1FAE5', color: '#10B981' }, texto: 'Confianza alta' }
  if (confianza === 'media') return { style: { backgroundColor: '#FEF3C7', color: '#B45309' }, texto: 'Confianza media' }
  return { style: { backgroundColor: '#FEE2E2', color: '#EF4444' }, texto: 'Confianza baja' }
}

function OCRUploader({ onItemConfirmado }: OCRUploaderProps) {
  const [archivo, setArchivo] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [resultado, setResultado] = useState<OCRResponse | null>(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Valores editables del panel de revisión
  const [form, setForm] = useState<OCRResultado | null>(null)

  const onDrop = useCallback((aceptados: File[]) => {
    const archivoNuevo = aceptados[0]
    if (!archivoNuevo) return
    setError(null)
    setArchivo(archivoNuevo)
    // Revoca el preview anterior antes de crear uno nuevo
    setPreview((anterior) => {
      if (anterior) URL.revokeObjectURL(anterior)
      return URL.createObjectURL(archivoNuevo)
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      'image/jpeg': [],
      'image/png': [],
      'image/webp': [],
    },
  })

  // Libera el object URL al desmontar
  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  const resetear = () => {
    if (preview) URL.revokeObjectURL(preview)
    setArchivo(null)
    setPreview(null)
    setResultado(null)
    setCargando(false)
    setError(null)
    setForm(null)
  }

  const handleExtraer = async () => {
    if (!archivo) return
    setCargando(true)
    setError(null)
    try {
      const respuesta = await subirFotoOCR(archivo)
      setResultado(respuesta)
      setForm({ ...respuesta.datos_extraidos })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo procesar la imagen')
    } finally {
      setCargando(false)
    }
  }

  const actualizarTexto = (clave: keyof OCRResultado, valor: string) => {
    setForm((prev) => (prev ? { ...prev, [clave]: valor === '' ? null : valor } : prev))
  }

  const actualizarNumero = (clave: keyof OCRResultado, valor: string) => {
    const numero = valor === '' ? null : Number(valor)
    setForm((prev) =>
      prev ? { ...prev, [clave]: numero !== null && Number.isNaN(numero) ? null : numero } : prev,
    )
  }

  const handleConfirmar = () => {
    if (!form || !resultado) return
    onItemConfirmado({ ...form, foto_url: resultado.foto_url })
    resetear()
  }

  const chip = form ? chipConfianza(form.confianza) : null

  return (
    <div className="w-full">
      {/* SECCIÓN A — Área de carga (mientras no haya resultado) */}
      {!resultado && (
        <div className="flex flex-col gap-4">
          <div
            {...getRootProps()}
            style={{
              minHeight: 150,
              fontSize: 16,
              borderColor: '#4B52E8',
              backgroundColor: isDragActive ? '#F0F1FD' : 'transparent',
            }}
            className="flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center"
          >
            <input {...getInputProps()} />
            {preview ? (
              <img
                src={preview}
                alt="Vista previa"
                style={{ maxHeight: 200 }}
                className="rounded-lg object-contain"
              />
            ) : (
              <>
                <span className="text-4xl">📷</span>
                <p className="mt-2 font-medium" style={{ color: '#0D0D0D' }}>Toca para subir una foto</p>
                <p className="mt-1 text-sm" style={{ color: '#6B7280' }}>JPG, PNG o WEBP · máx 10MB</p>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={handleExtraer}
            disabled={!archivo || cargando}
            className="font-semibold text-white disabled:opacity-60"
            style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, fontSize: 16 }}
          >
            {cargando ? 'Leyendo la etiqueta...' : 'Leer la etiqueta'}
          </button>
        </div>
      )}

      {/* SECCIÓN B — Panel de revisión (cuando hay resultado) */}
      {resultado && form && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ fontWeight: 700, fontSize: 16, color: '#0D0D0D' }}>Revisa y corrige los datos</h3>
            {chip && (
              <span className="rounded-full px-3 py-1 text-sm font-semibold" style={chip.style}>
                {chip.texto}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {CAMPOS_TEXTO.map(({ clave, etiqueta }) => (
              <label key={clave} className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
                {etiqueta}
                <input
                  type="text"
                  value={(form[clave] as string | null) ?? ''}
                  onChange={(e) => actualizarTexto(clave, e.target.value)}
                  style={inputStyle}
                  className={inputClase}
                />
              </label>
            ))}
            {CAMPOS_NUMERO.map(({ clave, etiqueta }) => (
              <label key={clave} className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
                {etiqueta}
                <input
                  type="number"
                  value={(form[clave] as number | null) ?? ''}
                  onChange={(e) => actualizarNumero(clave, e.target.value)}
                  style={inputStyle}
                  className={inputClase}
                />
              </label>
            ))}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleConfirmar}
              className="flex-1 font-semibold text-white"
              style={{ minHeight: 48, backgroundColor: '#10B981', borderRadius: 8, fontSize: 16 }}
            >
              Agregar producto
            </button>
            <button
              type="button"
              onClick={resetear}
              className="flex-1 font-semibold"
              style={{ minHeight: 48, backgroundColor: '#F3F4F6', color: '#0D0D0D', borderRadius: 8, fontSize: 16 }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* SECCIÓN C — Error */}
      {error && <p className="mt-4 text-center text-sm" style={{ color: '#EF4444' }}>{error}</p>}
    </div>
  )
}

export default OCRUploader
