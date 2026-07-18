import { useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useConfirmStore } from '../store/confirmStore'

// Modal de confirmación propio (reemplaza window.confirm). Se monta una sola vez
// en la raíz de la app; se dispara con `confirmar(...)` desde cualquier lado.
function ConfirmDialog() {
  const { t } = useTranslation()
  const { abierto, opts, responder } = useConfirmStore()
  const confirmarRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!abierto) return
    confirmarRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') responder(false)
      if (e.key === 'Enter') responder(true)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [abierto, responder])

  if (!abierto || !opts) return null
  const peligro = opts.peligro

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(13,13,13,0.45)' }}
      onClick={() => responder(false)}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="w-full max-w-sm rounded-2xl bg-white p-5"
        style={{ boxShadow: '0 20px 50px rgba(0,0,0,0.3)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {opts.titulo && (
          <h2 className="mb-2" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
            {opts.titulo}
          </h2>
        )}
        <p className="text-sm" style={{ color: '#374151', lineHeight: 1.5 }}>
          {opts.mensaje}
        </p>
        <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={() => responder(false)}
            className="rounded-lg border font-semibold"
            style={{ minHeight: 44, padding: '0 18px', borderColor: '#E5E7EB', color: '#374151', fontSize: 15 }}
          >
            {opts.textoCancelar ?? t('comun.cancelar')}
          </button>
          <button
            ref={confirmarRef}
            type="button"
            onClick={() => responder(true)}
            className="rounded-lg font-semibold text-white"
            style={{
              minHeight: 44,
              padding: '0 18px',
              backgroundColor: peligro ? '#EF4444' : '#4B52E8',
              fontSize: 15,
            }}
          >
            {opts.textoConfirmar ?? t('comun.confirmar')}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfirmDialog
