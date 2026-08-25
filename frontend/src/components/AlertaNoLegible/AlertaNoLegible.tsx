import { useTranslation } from 'react-i18next'
import { AlertTriangle } from 'lucide-react'
import type { Legibilidad } from '../../lib/legibilidad'

interface Props {
  legibilidad: Legibilidad
  // compacta = versión chica para tarjetas de carga masiva
  compacta?: boolean
}

// Alerta que avisa que una foto no es legible (imagen mala o datos faltantes)
// y pide volver a tomarla. Se muestra en el idioma activo de la app.
function AlertaNoLegible({ legibilidad, compacta = false }: Props) {
  const { t } = useTranslation()
  const { imagenIlegible, motivo, faltantes } = legibilidad

  // Motivo traducido (el modelo lo devuelve en español; lo mapeamos al idioma activo)
  const claveMotivo = (motivo ?? '').toLowerCase().replace(/\s+/g, '_')
  const motivoTraducido = t([`ocr.motivos.${claveMotivo}`, 'ocr.motivos.generico'])

  // Falla NUESTRA (API caída o sin crédito), no de la foto. Volver a tomarla no
  // arregla nada, así que el mensaje tiene que decirlo con todas las letras en vez
  // de mandar a la vendedora a repetir el trabajo.
  const sinSaldo = claveMotivo === 'sin_saldo'
  const esErrorSistema = claveMotivo === 'error_sistema' || sinSaldo

  // Lista de datos faltantes traducida
  const camposFaltantes = faltantes.map((k) => t(`ocr.${k}`)).join(', ')

  return (
    <div
      className="rounded-xl border"
      style={{
        backgroundColor: '#FEF2F2',
        borderColor: '#FCA5A5',
        padding: compacta ? 10 : 14,
      }}
      role="alert"
    >
      <div className="flex items-start gap-2">
        <AlertTriangle size={compacta ? 16 : 20} style={{ color: 'var(--yuda-error)', flexShrink: 0, marginTop: 1 }} />
        <div className="flex flex-col gap-1">
          <p className="font-semibold" style={{ color: 'var(--yuda-error-dark)', fontSize: compacta ? 13 : 15 }}>
            {t(sinSaldo ? 'ocr.sinSaldoTitulo' : esErrorSistema ? 'ocr.errorSistemaTitulo' : 'ocr.noLegibleTitulo')}
          </p>

          {esErrorSistema && (
            <p style={{ color: '#7F1D1D', fontSize: compacta ? 12 : 14 }}>
              {t(sinSaldo ? 'ocr.sinSaldoTexto' : 'ocr.errorSistemaTexto')}
            </p>
          )}

          {!esErrorSistema && imagenIlegible && (
            <p style={{ color: '#7F1D1D', fontSize: compacta ? 12 : 14 }}>
              {motivo
                ? t('ocr.noLegibleImagen', { motivo: motivoTraducido })
                : t('ocr.noLegibleImagenSin')}
            </p>
          )}

          {!esErrorSistema && faltantes.length > 0 && (
            <p style={{ color: '#7F1D1D', fontSize: compacta ? 12 : 14 }}>
              {t('ocr.noLegibleFaltan', { campos: camposFaltantes })}
            </p>
          )}

          {!compacta && !esErrorSistema && (
            <p style={{ color: '#7F1D1D', fontSize: 13 }}>{t('ocr.noLegibleInstruccion')}</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default AlertaNoLegible
