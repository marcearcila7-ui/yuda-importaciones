import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import axios from 'axios'
import { magicLoginPortal } from '../../api/portal'
import { usePortalStore } from '../../store/portalStore'

// Entra al portal con el enlace de un aviso automático (ej. "tu pedido está
// listo para aprobar"), sin pedir contraseña: el cliente no siempre la
// recuerda, y no hay quien la escriba a mano en un mensaje automático.
function PortalEntrar() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const loginConToken = usePortalStore((s) => s.loginConToken)
  const [error, setError] = useState<string | null>(null)
  // El token de un solo uso solo debe canjearse una vez, ni siquiera si
  // React vuelve a montar el componente en dev (StrictMode).
  const yaIntentado = useRef(false)

  useEffect(() => {
    if (yaIntentado.current) return
    yaIntentado.current = true
    const token = searchParams.get('token')
    if (!token) {
      setError(t('portal.enlaceInvalido'))
      return
    }
    magicLoginPortal(token)
      .then((data) => {
        loginConToken(data.access_token, data.cliente)
        navigate(`/portal/cotizacion/${data.sesion_id}`, { replace: true })
      })
      .catch((err) => {
        const mensaje = (axios.isAxiosError(err) && err.response?.data?.detail) || t('portal.enlaceInvalido')
        setError(mensaje)
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-white px-6 text-center">
      <img
        src="/logo-yuda-importaciones.svg"
        alt="YUDA Importaciones"
        style={{ width: 160, height: 'auto' }}
      />
      {error ? (
        <>
          <p style={{ color: 'var(--yuda-error)', fontSize: 15 }}>{error}</p>
          <button
            type="button"
            onClick={() => navigate('/portal/login')}
            className="mt-2 rounded-lg px-4 py-2 text-sm font-semibold text-white"
            style={{ backgroundColor: 'var(--yuda-primary)' }}
          >
            {t('portal.irALogin')}
          </button>
        </>
      ) : (
        <p style={{ color: 'var(--yuda-text-secondary)', fontSize: 15 }}>{t('portal.entrando')}</p>
      )}
    </div>
  )
}

export default PortalEntrar
