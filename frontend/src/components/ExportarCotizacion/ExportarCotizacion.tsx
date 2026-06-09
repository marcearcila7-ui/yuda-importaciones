import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
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

  const items = usePackingStore((s) => s.items)
  // Foto 1 (producto con datos): obligatoria para generar. La cargan el OCR.
  const sinFotoDatos = items.filter((i) => !i.foto_url).length
  // Datos clave que deberían haberse extraído (precio + alguna descripción).
  const sinDatos = items.filter(
    (i) => !i.price_rmb || !(i.descripcion_es || i.descripcion_en || i.descripcion_zh),
  ).length
  // Foto 2 (final): opcional; las que no la tengan usan la de datos como respaldo.
  const conFotoFinal = items.filter((i) => i.foto_final_url).length
  const sinProductos = items.length === 0
  // No se puede generar sin productos, sin la foto de datos en todos, ni sin confirmar.
  const bloqueado = sinProductos || sinFotoDatos > 0 || !confirmado

  const descargar = async (tipo: 'excel' | 'pdf') => {
    if (bloqueado) return
    setError(null)
    setGenerando(tipo)
    // En iPhone/Safari la pestaña debe abrirse dentro del toque (antes del await)
    const ventana = window.open('', '_blank')
    try {
      const blob =
        tipo === 'excel'
          ? await exportarCotizacionExcel(sesion_id, idioma)
          : await exportarCotizacionPDF(sesion_id, idioma)
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
      <h2 style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>{t('cotizacion.titulo')}</h2>
      <p className="text-sm" style={{ color: '#6B7280' }}>{t('cotizacion.ayuda')}</p>

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
                backgroundColor: activo ? '#4B52E8' : 'transparent',
                color: activo ? '#FFFFFF' : '#6B7280',
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

      {/* Antes de generar: confirmar extracción y fotos según su propósito */}
      <div className="rounded-xl border p-3" style={{ borderColor: '#E5E7EB', backgroundColor: '#F9FAFB' }}>
        <p className="mb-2 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
          {t('cotizacion.confirmTitulo')}
        </p>
        {sinProductos ? (
          <p className="flex items-center gap-2 text-sm" style={{ color: '#B45309' }}>
            <AlertTriangle size={15} /> {t('cotizacion.sinProductos')}
          </p>
        ) : (
          <div className="flex flex-col gap-1.5 text-sm">
            <p style={{ color: '#6B7280' }}>{t('cotizacion.prodCount', { n: items.length })}</p>
            {/* Foto de datos (obligatoria) */}
            {sinFotoDatos > 0 ? (
              <p className="flex items-center gap-2" style={{ color: '#EF4444' }}>
                <AlertTriangle size={15} /> {t('cotizacion.faltaFotoDatos', { n: sinFotoDatos })}
              </p>
            ) : (
              <p className="flex items-center gap-2" style={{ color: '#10B981' }}>
                <CheckCircle2 size={15} /> {t('cotizacion.fotoDatosOk')}
              </p>
            )}
            {/* Extracción de datos */}
            {sinDatos > 0 && (
              <p className="flex items-center gap-2" style={{ color: '#B45309' }}>
                <AlertTriangle size={15} /> {t('cotizacion.revisarDatos', { n: sinDatos })}
              </p>
            )}
            {/* Foto final (opcional, con respaldo) */}
            <p style={{ color: '#6B7280' }}>
              {t('cotizacion.fotoFinalResumen', { con: conFotoFinal, sin: items.length - conFotoFinal })}
            </p>
            {/* Confirmación explícita */}
            <label className="mt-1 flex items-start gap-2" style={{ color: '#0D0D0D' }}>
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
          disabled={generando !== null || bloqueado}
          className="flex flex-1 items-center justify-center gap-2 text-white disabled:opacity-60"
          style={{ ...btnDescarga, backgroundColor: '#10B981' }}
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
          disabled={generando !== null || bloqueado}
          className="flex flex-1 items-center justify-center gap-2 text-white disabled:opacity-60"
          style={{ ...btnDescarga, backgroundColor: '#4B52E8' }}
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

      {error && <p className="text-center text-sm" style={{ color: '#EF4444' }}>{error}</p>}
    </div>
  )
}

export default ExportarCotizacion
