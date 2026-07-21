import { useTranslation } from 'react-i18next'
import { AlertTriangle, Camera, Check, X } from 'lucide-react'

interface Props {
  onConfirmar: () => void
  onCancelar: () => void
}

// Modal grande y BLOQUEANTE que aparece al iniciar/abrir una cotización.
// Recuerda cómo tomar bien las fotos y qué datos deben quedar legibles; no deja
// continuar hasta que la vendedora confirma que sus fotos cumplen. i18n es/en/zh.
function AdvertenciaFotos({ onConfirmar, onCancelar }: Props) {
  const { t } = useTranslation()

  const comoTomar: string[] = t('advertenciaFotos.como', { returnObjects: true }) as string[]
  const datos: string[] = t('advertenciaFotos.datos', { returnObjects: true }) as string[]

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.75)' }}
      role="alertdialog"
      aria-modal="true"
    >
      <div
        className="flex max-h-[92vh] w-full max-w-2xl flex-col overflow-y-auto rounded-2xl bg-white"
        style={{ boxShadow: '0 20px 60px rgba(0,0,0,0.4)' }}
      >
        {/* Encabezado de alerta */}
        <div className="flex items-start gap-3 rounded-t-2xl p-5 sm:p-6" style={{ backgroundColor: 'var(--yuda-error)' }}>
          <AlertTriangle size={30} color="#fff" style={{ flexShrink: 0 }} />
          <div>
            <h2 style={{ fontWeight: 800, fontSize: 22, color: '#fff', lineHeight: 1.15 }}>
              {t('advertenciaFotos.titulo')}
            </h2>
            <p className="mt-1 text-sm" style={{ color: '#FFE4E6' }}>{t('advertenciaFotos.subtitulo')}</p>
          </div>
        </div>

        <div className="flex flex-col gap-5 p-5 sm:p-6">
          {/* Cómo tomar la foto */}
          <section>
            <h3 className="mb-2 flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
              <Camera size={18} /> {t('advertenciaFotos.comoTitulo')}
            </h3>
            <ul className="flex flex-col gap-2">
              {comoTomar.map((linea, i) => (
                <li key={i} className="flex items-start gap-2 text-sm" style={{ color: 'var(--yuda-text)' }}>
                  <Check size={16} style={{ color: 'var(--yuda-success)', flexShrink: 0, marginTop: 2 }} />
                  <span>{linea}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Datos que deben quedar legibles */}
          <section className="rounded-xl p-4" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
            <h3 className="mb-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-primary)' }}>
              {t('advertenciaFotos.datosTitulo')}
            </h3>
            <div className="flex flex-wrap gap-2">
              {datos.map((d, i) => (
                <span key={i} className="rounded-full bg-white px-3 py-1 text-sm font-semibold" style={{ color: 'var(--yuda-primary)' }}>
                  {d}
                </span>
              ))}
            </div>
          </section>

          {/* Consecuencia */}
          <p className="rounded-lg px-3 py-2 text-sm font-medium" style={{ backgroundColor: '#FEF2F2', color: 'var(--yuda-error-dark)' }}>
            {t('advertenciaFotos.consecuencia')}
          </p>

          {/* Acciones */}
          <div className="flex flex-col gap-2 sm:flex-row-reverse">
            <button
              type="button"
              onClick={onConfirmar}
              className="flex min-h-[52px] flex-1 items-center justify-center gap-2 rounded-lg font-semibold text-white"
              style={{ backgroundColor: 'var(--yuda-success)', fontSize: 16 }}
            >
              <Check size={18} /> {t('advertenciaFotos.confirmar')}
            </button>
            <button
              type="button"
              onClick={onCancelar}
              className="flex min-h-[52px] items-center justify-center gap-2 rounded-lg border font-medium sm:px-6"
              style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-secondary)', fontSize: 16 }}
            >
              <X size={18} /> {t('advertenciaFotos.cancelar')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AdvertenciaFotos
