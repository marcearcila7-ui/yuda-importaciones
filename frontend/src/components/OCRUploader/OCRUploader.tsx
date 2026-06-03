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
const botonStyle: CSSProperties = { minHeight: 48, fontSize: 16 }
const dropzoneStyle: CSSProperties = { minHeight: 150, fontSize: 16 }

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

function chipConfianza(confianza: OCRResultado['confianza']) {
  if (confianza === 'alta') return { clase: 'bg-green-100 text-green-800', texto: 'Confianza alta' }
  if (confianza === 'media') return { clase: 'bg-yellow-100 text-yellow-800', texto: 'Confianza media' }
  return { clase: 'bg-red-100 text-red-800', texto: 'Confianza baja' }
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
    <div className="mx-auto w-full max-w-2xl p-4">
      {/* SECCIÓN A — Área de carga (mientras no haya resultado) */}
      {!resultado && (
        <div className="flex flex-col gap-4">
          <div
            {...getRootProps()}
            style={dropzoneStyle}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center ${
              isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
            }`}
          >
            <input {...getInputProps()} />
            {preview ? (
              <img
                src={preview}
                alt="Vista previa"
                style={{ maxHeight: 200 }}
                className="rounded object-contain"
              />
            ) : (
              <>
                <span className="text-4xl">📷</span>
                <p className="mt-2 font-medium text-gray-700">Tocá para subir una foto</p>
                <p className="mt-1 text-sm text-gray-500">JPG, PNG o WEBP · máx 10MB</p>
              </>
            )}
          </div>

          <button
            type="button"
            onClick={handleExtraer}
            disabled={!archivo || cargando}
            style={botonStyle}
            className="rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {cargando ? 'Analizando etiqueta...' : 'Extraer datos'}
          </button>
        </div>
      )}

      {/* SECCIÓN B — Panel de revisión (cuando hay resultado) */}
      {resultado && form && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">Revisar datos extraídos</h2>
            {chip && (
              <span className={`rounded-full px-3 py-1 text-sm font-medium ${chip.clase}`}>
                {chip.texto}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {CAMPOS_TEXTO.map(({ clave, etiqueta }) => (
              <label key={clave} className="flex flex-col gap-1 text-sm text-gray-700">
                {etiqueta}
                <input
                  type="text"
                  value={(form[clave] as string | null) ?? ''}
                  onChange={(e) => actualizarTexto(clave, e.target.value)}
                  style={inputStyle}
                  className="rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                />
              </label>
            ))}
            {CAMPOS_NUMERO.map(({ clave, etiqueta }) => (
              <label key={clave} className="flex flex-col gap-1 text-sm text-gray-700">
                {etiqueta}
                <input
                  type="number"
                  value={(form[clave] as number | null) ?? ''}
                  onChange={(e) => actualizarNumero(clave, e.target.value)}
                  style={inputStyle}
                  className="rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
                />
              </label>
            ))}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleConfirmar}
              style={botonStyle}
              className="flex-1 rounded bg-green-600 px-4 font-semibold text-white hover:bg-green-700"
            >
              Agregar al Packing List
            </button>
            <button
              type="button"
              onClick={resetear}
              style={botonStyle}
              className="flex-1 rounded bg-gray-200 px-4 font-semibold text-gray-800 hover:bg-gray-300"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* SECCIÓN C — Error */}
      {error && <p className="mt-4 text-center text-sm text-red-600">{error}</p>}
    </div>
  )
}

export default OCRUploader
