import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import { exportarCotizacionExcel, exportarCotizacionPDF } from '../../api/packing'

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

  const descargar = async (tipo: 'excel' | 'pdf') => {
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

      <div className="flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => descargar('excel')}
          disabled={generando !== null}
          className="flex-1 text-white disabled:opacity-60"
          style={{ ...btnDescarga, backgroundColor: '#10B981' }}
        >
          {generando === 'excel' ? t('cotizacion.generando') : t('cotizacion.descargarExcel')}
        </button>
        <button
          type="button"
          onClick={() => descargar('pdf')}
          disabled={generando !== null}
          className="flex-1 text-white disabled:opacity-60"
          style={{ ...btnDescarga, backgroundColor: '#4B52E8' }}
        >
          {generando === 'pdf' ? t('cotizacion.generando') : t('cotizacion.descargarPDF')}
        </button>
      </div>

      {error && <p className="text-center text-sm" style={{ color: '#EF4444' }}>{error}</p>}
    </div>
  )
}

export default ExportarCotizacion
