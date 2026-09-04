import { useCallback, useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useDropzone } from 'react-dropzone'
import { useTranslation } from 'react-i18next'
import { Camera, Sparkles } from 'lucide-react'
import { subirFotoOCR } from '../../api/ocr'
import { comprimirImagen } from '../../lib/comprimirImagen'
import { CAMPOS_OBLIGATORIOS, evaluarLegibilidad } from '../../lib/legibilidad'
import AlertaNoLegible from '../AlertaNoLegible/AlertaNoLegible'
import AvisoDosMinimos from '../AvisoDosMinimos/AvisoDosMinimos'
import type { OCRResponse, OCRResultado } from '../../types/ocr'

interface OCRUploaderProps {
  onItemConfirmado: (datos: OCRResultado & { foto_url: string }) => void
}

// Requisitos críticos de mobile
const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

// Campos numéricos editables (clave del dato + clave de traducción)
const CAMPOS_NUMERO: Array<{ clave: keyof OCRResultado; i18n: string }> = [
  { clave: 'price_rmb', i18n: 'precioRMB' },
  { clave: 'qty_por_ctn', i18n: 'unidPorCaja' },
  { clave: 'cantidad_minima', i18n: 'mqt' },
  { clave: 'cbm_directo', i18n: 'cbm' },
  { clave: 'largo_cm', i18n: 'largoCm' },
  { clave: 'ancho_cm', i18n: 'anchoCm' },
  { clave: 'alto_cm', i18n: 'altoCm' },
]

// Datos obligatorios (por su clave i18n) para resaltar los que faltan.
const REQUERIDOS = new Set(CAMPOS_OBLIGATORIOS.map((c) => c.i18n))

// Campos de texto editables
const CAMPOS_TEXTO: Array<{ clave: keyof OCRResultado; i18n: string }> = [
  { clave: 'supplier_nombre', i18n: 'proveedor' },
  { clave: 'supplier_numero', i18n: 'nStand' },
  { clave: 'colores', i18n: 'colores' },
  { clave: 'descripcion_zh', i18n: 'descripcionZh' },
]

function chipConfianza(confianza: OCRResultado['confianza']): { style: CSSProperties; i18n: string } {
  if (confianza === 'alta') return { style: { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }, i18n: 'confianzaAlta' }
  if (confianza === 'media') return { style: { backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }, i18n: 'confianzaMedia' }
  return { style: { backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }, i18n: 'confianzaBaja' }
}

function OCRUploader({ onItemConfirmado }: OCRUploaderProps) {
  const { t } = useTranslation()
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
    // Al elegir/reemplazar una foto, se descarta el resultado anterior para
    // volver a la pantalla de análisis con la nueva imagen.
    setResultado(null)
    setForm(null)
    // Revoca el preview anterior antes de crear uno nuevo
    setPreview((anterior) => {
      if (anterior) URL.revokeObjectURL(anterior)
      return URL.createObjectURL(archivoNuevo)
    })
  }, [])

  // Se listan las extensiones además del MIME porque en Android muchas fotos
  // llegan con el type vacío o "application/octet-stream" (Google Fotos, Drive,
  // imágenes de WhatsApp) y el filtro por MIME solo las descartaba sin avisar.
  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    onDropRejected: () => setError(t('ocr.archivoNoSoportado')),
    multiple: false,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/webp': ['.webp'],
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
      const comprimido = await comprimirImagen(archivo)
      const respuesta = await subirFotoOCR(comprimido)
      setResultado(respuesta)
      setForm({ ...respuesta.datos_extraidos })
    } catch (err) {
      setError(err instanceof Error ? err.message : t('ocr.errorProcesar'))
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
  // Legibilidad evaluada sobre el FORMULARIO editable: así, si la vendedora completa
  // a mano los datos obligatorios (o reintenta con IA), la tarjeta se desbloquea.
  const legibilidad = form ? evaluarLegibilidad(form) : null
  const faltaSet = new Set(legibilidad?.faltantes ?? [])

  return (
    <div className="w-full">
      {/* SECCIÓN A — Área de carga (mientras no haya resultado) */}
      {!resultado && (
        <div className="flex flex-col gap-4">
          <div
            {...getRootProps()}
            style={{
              fontSize: 16,
              borderColor: 'var(--yuda-primary)',
              backgroundColor: isDragActive ? '#F0F1FD' : 'transparent',
            }}
            className="flex min-h-[200px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center sm:min-h-[150px]"
          >
            <input {...getInputProps()} />
            {preview ? (
              <img
                src={preview}
                alt="Vista previa"
                className="max-h-[250px] w-full rounded-lg object-contain sm:max-h-[200px]"
              />
            ) : (
              <>
                <Camera size={32} />
                <p className="mt-3 text-lg font-semibold sm:mt-2 sm:text-base sm:font-medium" style={{ color: 'var(--yuda-accent)' }}>{t('ocr.instruccion')}</p>
                <p className="mt-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('ocr.formatos')}</p>
              </>
            )}
          </div>

          {/* CTA de cámara prominente: solo mobile (si todavía no hay imagen) */}
          {!preview && (
            <button
              type="button"
              onClick={open}
              className="flex min-h-[52px] w-full items-center justify-center gap-2 rounded-lg font-semibold text-white sm:hidden"
              style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 16 }}
            >
              <Camera size={16} /> {t('ocr.tomarFoto')}
            </button>
          )}

          <button
            type="button"
            onClick={handleExtraer}
            disabled={!archivo || cargando}
            className="min-h-[52px] w-full font-semibold text-white disabled:opacity-60 sm:min-h-[48px]"
            style={{ backgroundColor: 'var(--yuda-primary)', borderRadius: 8, fontSize: 16 }}
          >
            {cargando ? t('ocr.analizando') : t('ocr.extraer')}
          </button>
        </div>
      )}

      {/* SECCIÓN B — Panel de revisión (foto legible O no): siempre editable.
          Si no es usable, muestra el motivo + acciones de IA, pero permite
          completar a mano; el botón "Agregar" se habilita cuando están los datos. */}
      {resultado && form && legibilidad && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>{t('ocr.revisarDatos')}</h3>
            {chip && (
              <span className="rounded-full px-3 py-1 text-sm font-semibold" style={chip.style}>
                {t(`ocr.${chip.i18n}`)}
              </span>
            )}
          </div>

          {(preview || resultado.foto_url) && (
            <img
              src={preview ?? resultado.foto_url}
              alt="Vista previa"
              className="max-h-[250px] w-full rounded-lg object-contain sm:max-h-[200px]"
            />
          )}

          {/* Foto no usable: motivo amable + opciones (IA o reemplazar) */}
          {!legibilidad.ok && (
            <>
              <AlertaNoLegible legibilidad={legibilidad} />
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={handleExtraer}
                  disabled={cargando}
                  className="flex flex-1 items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
                  style={{ minHeight: 48, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, fontSize: 16 }}
                >
                  <Sparkles size={16} /> {cargando ? t('ocr.analizando') : t('ocr.reintentarIA')}
                </button>
                <button
                  type="button"
                  onClick={open}
                  className="flex flex-1 items-center justify-center gap-2 font-semibold"
                  style={{ minHeight: 48, backgroundColor: '#F3F4F6', color: 'var(--yuda-accent)', borderRadius: 8, fontSize: 16 }}
                >
                  <Camera size={16} /> {t('ocr.reemplazarFoto')}
                </button>
              </div>
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('ocr.oCompletaManual')}</p>
            </>
          )}

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {CAMPOS_TEXTO.map(({ clave, i18n }) => (
              <label key={clave} className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t(`ocr.${i18n}`)}
                {REQUERIDOS.has(i18n) && <span style={{ color: 'var(--yuda-error)' }}> *</span>}
                <input
                  type="text"
                  value={(form[clave] as string | null) ?? ''}
                  onChange={(e) => actualizarTexto(clave, e.target.value)}
                  style={{ ...inputStyle, borderColor: faltaSet.has(i18n) ? 'var(--yuda-error)' : undefined }}
                  className={`${inputClase} min-h-[48px] sm:min-h-0`}
                />
              </label>
            ))}
            {CAMPOS_NUMERO.map(({ clave, i18n }) => (
              <label key={clave} className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t(`ocr.${i18n}`)}
                {REQUERIDOS.has(i18n) && <span style={{ color: 'var(--yuda-error)' }}> *</span>}
                <input
                  type="number"
                  value={(form[clave] as number | null) ?? ''}
                  onChange={(e) => actualizarNumero(clave, e.target.value)}
                  style={{ ...inputStyle, borderColor: faltaSet.has(i18n) ? 'var(--yuda-error)' : undefined }}
                  className={`${inputClase} min-h-[48px] sm:min-h-0`}
                />
                {clave === 'cantidad_minima' && (
                  <AvisoDosMinimos
                    actual={form.cantidad_minima}
                    tienda={form.cantidad_minima_tienda}
                    onElegir={(v) => setForm((prev) => (prev ? { ...prev, cantidad_minima: v } : prev))}
                  />
                )}
              </label>
            ))}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={handleConfirmar}
              disabled={!legibilidad.ok}
              className="flex-1 font-semibold text-white disabled:opacity-60"
              style={{ minHeight: 48, backgroundColor: 'var(--yuda-success)', borderRadius: 8, fontSize: 16 }}
            >
              {t('ocr.agregarPacking')}
            </button>
            <button
              type="button"
              onClick={resetear}
              className="flex-1 font-semibold"
              style={{ minHeight: 48, backgroundColor: '#F3F4F6', color: 'var(--yuda-accent)', borderRadius: 8, fontSize: 16 }}
            >
              {t('ocr.cancelar')}
            </button>
          </div>
        </div>
      )}

      {/* SECCIÓN C — Error */}
      {error && <p className="mt-4 text-center text-sm" style={{ color: 'var(--yuda-error)' }}>{error}</p>}
    </div>
  )
}

export default OCRUploader
