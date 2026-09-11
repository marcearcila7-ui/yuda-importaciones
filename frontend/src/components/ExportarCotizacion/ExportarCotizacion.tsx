import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, CheckCircle2, FileSpreadsheet, FileText } from 'lucide-react'
import { exportarCotizacionExcel, exportarCotizacionPDF } from '../../api/packing'
import { usePackingStore } from '../../store/packingStore'

interface ExportarCotizacionProps {
  sesion_id: string
  nombre_cliente: string
}

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

// Mismo orden y claves que CLAVES_COLUMNAS en cotizacion_service.py: cambiar
// una lista sin la otra hace que las columnas salgan desordenadas o con
// nombres sin traducir.
const CLAVES_COLUMNAS = [
  'numero', 'fecha_recibo', 'shipping_mark', 'foto', 'referencia', 'codigo',
  'desc_es', 'desc_en', 'desc_zh', 'material', 'uso',
  'cajas', 'uds_caja', 'unidad', 'cant_total',
  'precio_rmb', 'total_rmb', 'precio_usd', 'total_usd',
  'largo', 'ancho', 'alto', 'cbm', 't_cbm',
  'peso', 'peso_total', 'mqt', 'marca',
] as const

// Sin foto o referencia el cliente no puede identificar el producto: no se
// pueden desmarcar (el backend también las fuerza, por si acaso).
const COLUMNAS_OBLIGATORIAS = new Set(['foto', 'referencia'])

const btnDescarga: CSSProperties = {
  minHeight: 48,
  borderRadius: 8,
  fontSize: 16,
  fontWeight: 600,
  padding: '0 20px',
}

function ExportarCotizacion({ sesion_id, nombre_cliente }: ExportarCotizacionProps) {
  const { t, i18n } = useTranslation()
  const inicial = ['es', 'en', 'zh'].includes(i18n.language) ? i18n.language : 'es'
  const [idioma, setIdioma] = useState(inicial)
  const [generando, setGenerando] = useState<'excel' | 'pdf' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirmado, setConfirmado] = useState(false)
  // Qué columnas va a traer el documento. Todas marcadas por defecto: hay que
  // desmarcar a propósito para ocultar algo, nunca al revés.
  const [columnasActivas, setColumnasActivas] = useState<Set<string>>(() => new Set(CLAVES_COLUMNAS))
  const toggleColumna = (clave: string) => {
    if (COLUMNAS_OBLIGATORIAS.has(clave)) return
    setColumnasActivas((prev) => {
      const siguiente = new Set(prev)
      if (siguiente.has(clave)) siguiente.delete(clave)
      else siguiente.add(clave)
      return siguiente
    })
  }

  const items = usePackingStore((s) => s.items)
  // Foto 1 (producto con datos): obligatoria para generar. La cargan el OCR.
  const sinFotoDatos = items.filter((i) => !i.foto_url).length
  // Datos clave que deberían haberse extraído (precio + alguna descripción).
  const sinDatos = items.filter(
    (i) => !i.price_rmb || !(i.descripcion_es || i.descripcion_en || i.descripcion_zh),
  ).length
  const sinProductos = items.length === 0
  // No se puede generar sin productos, sin la foto de datos en todos, ni sin confirmar.
  const bloqueado = sinProductos || sinFotoDatos > 0 || !confirmado
  // Antes el boton bloqueado simplemente no respondia (disabled nativo no dispara
  // onClick): habia que leer la lista de arriba para entender por que. Ahora, al
  // tocarlo, dice exactamente cual de los tres motivos falta.
  const motivoBloqueo = sinProductos
    ? t('cotizacion.sinProductos')
    : sinFotoDatos > 0
      ? t('cotizacion.faltaFotoDatos', { n: sinFotoDatos })
      : !confirmado
        ? t('cotizacion.faltaConfirmar')
        : null

  const descargar = async (tipo: 'excel' | 'pdf') => {
    if (bloqueado) {
      if (motivoBloqueo) toast.error(motivoBloqueo)
      return
    }
    setError(null)
    setGenerando(tipo)
    // En iPhone/Safari la pestaña debe abrirse dentro del toque (antes del await)
    const ventana = window.open('', '_blank')
    try {
      const columnas = Array.from(columnasActivas)
      const blob =
        tipo === 'excel'
          ? await exportarCotizacionExcel(sesion_id, idioma, columnas)
          : await exportarCotizacionPDF(sesion_id, idioma, columnas)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        const enlace = document.createElement('a')
        enlace.href = url
        enlace.download = `Cotizacion_${nombre_cliente}_${idioma}.${tipo === 'excel' ? 'xlsx' : 'pdf'}`
        enlace.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      ventana?.close()
      setError(t('cotizacion.error'))
    } finally {
      setGenerando(null)
    }
  }

  return (
    <div className="card flex flex-col gap-4">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('cotizacion.titulo')}</h2>
      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cotizacion.ayuda')}</p>

      {/* Selector de idioma */}
      <div className="flex gap-1">
        {IDIOMAS.map((idi) => {
          const activo = idioma === idi.code
          return (
            <button
              key={idi.code}
              type="button"
              onClick={() => setIdioma(idi.code)}
              style={{
                borderRadius: 6,
                backgroundColor: activo ? 'var(--yuda-primary)' : 'transparent',
                color: activo ? 'var(--yuda-white)' : 'var(--yuda-text-secondary)',
                padding: '6px 14px',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              {idi.label}
            </button>
          )
        })}
      </div>

      {/* Qué columnas va a traer el documento. Todas activas por defecto. */}
      <div className="rounded-xl border p-3" style={{ borderColor: 'var(--yuda-border)' }}>
        <p className="mb-1 text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
          {t('cotizacion.columnasTitulo')}
        </p>
        <p className="mb-2 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('cotizacion.columnasAyuda')}
        </p>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 sm:grid-cols-3">
          {CLAVES_COLUMNAS.map((clave) => {
            const obligatoria = COLUMNAS_OBLIGATORIAS.has(clave)
            return (
              <label
                key={clave}
                className="flex items-center gap-1.5 text-sm"
                style={{ color: obligatoria ? 'var(--yuda-text-secondary)' : 'var(--yuda-accent)' }}
              >
                <input
                  type="checkbox"
                  checked={obligatoria || columnasActivas.has(clave)}
                  disabled={obligatoria}
                  onChange={() => toggleColumna(clave)}
                  style={{ width: 15, height: 15, flexShrink: 0 }}
                />
                <span className="truncate">
                  {t(`cotizacion.columnas.${clave}`)}
                  {obligatoria && (
                    <span className="text-xs italic"> ({t('cotizacion.columnaObligatoria')})</span>
                  )}
                </span>
              </label>
            )
          })}
        </div>
      </div>

      {/* Antes de generar: confirmar extracción y fotos según su propósito */}
      <div className="rounded-xl border p-3" style={{ borderColor: 'var(--yuda-border)', backgroundColor: '#F9FAFB' }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
          {t('cotizacion.confirmTitulo')}
        </p>
        {sinProductos ? (
          <p className="flex items-center gap-2 text-sm" style={{ color: 'var(--yuda-warning-dark)' }}>
            <AlertTriangle size={15} /> {t('cotizacion.sinProductos')}
          </p>
        ) : (
          <div className="flex flex-col gap-1.5 text-sm">
            <p style={{ color: 'var(--yuda-text-secondary)' }}>{t('cotizacion.prodCount', { n: items.length })}</p>
            {/* Foto de datos (obligatoria) */}
            {sinFotoDatos > 0 ? (
              <p className="flex items-center gap-2" style={{ color: 'var(--yuda-error)' }}>
                <AlertTriangle size={15} /> {t('cotizacion.faltaFotoDatos', { n: sinFotoDatos })}
              </p>
            ) : (
              <p className="flex items-center gap-2" style={{ color: 'var(--yuda-success)' }}>
                <CheckCircle2 size={15} /> {t('cotizacion.fotoDatosOk')}
              </p>
            )}
            {/* Extracción de datos */}
            {sinDatos > 0 && (
              <p className="flex items-center gap-2" style={{ color: 'var(--yuda-warning-dark)' }}>
                <AlertTriangle size={15} /> {t('cotizacion.revisarDatos', { n: sinDatos })}
              </p>
            )}
            {/* Confirmación explícita */}
            <label className="mt-1 flex items-start gap-2" style={{ color: 'var(--yuda-accent)' }}>
              <input
                type="checkbox"
                checked={confirmado}
                onChange={(e) => setConfirmado(e.target.checked)}
                style={{ marginTop: 3, width: 16, height: 16 }}
              />
              <span>{t('cotizacion.confirmCheck')}</span>
            </label>
          </div>
        )}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => descargar('excel')}
          disabled={generando !== null}
          aria-disabled={bloqueado}
          className="flex flex-1 items-center justify-center gap-2 text-white disabled:opacity-60"
          style={{ ...btnDescarga, backgroundColor: 'var(--yuda-success)', opacity: bloqueado ? 0.6 : 1 }}
        >
          {generando === 'excel' ? (
            t('cotizacion.generando')
          ) : (
            <>
              <FileSpreadsheet size={18} /> {t('cotizacion.descargarExcel')}
            </>
          )}
        </button>
        <button
          type="button"
          onClick={() => descargar('pdf')}
          disabled={generando !== null}
          aria-disabled={bloqueado}
          className="flex flex-1 items-center justify-center gap-2 text-white disabled:opacity-60"
          style={{ ...btnDescarga, backgroundColor: 'var(--yuda-primary)', opacity: bloqueado ? 0.6 : 1 }}
        >
          {generando === 'pdf' ? (
            t('cotizacion.generando')
          ) : (
            <>
              <FileText size={18} /> {t('cotizacion.descargarPDF')}
            </>
          )}
        </button>
      </div>

      {error && <p className="text-center text-sm" style={{ color: 'var(--yuda-error)' }}>{error}</p>}
    </div>
  )
}

export default ExportarCotizacion
