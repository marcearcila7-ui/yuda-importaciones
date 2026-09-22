import { useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import axios from 'axios'
import { cambiarPasswordPortal } from '../../api/portal'
import { usePortalStore } from '../../store/portalStore'

const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[var(--yuda-border)] bg-transparent focus:border-[var(--yuda-primary)] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: 'var(--yuda-text)', display: 'block' }

// Pantalla obligatoria cuando el cliente todavía tiene la clave de plantilla
// de la importación masiva de Yuda Contable (Cliente.debe_cambiar_password):
// no puede ver nada más del portal hasta que ponga una propia.
function PortalCambiarPassword() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { passwordCambiada } = usePortalStore()
  const [passwordActual, setPasswordActual] = useState('')
  const [passwordNueva, setPasswordNueva] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    if (passwordNueva.length < 6) {
      setError(t('portal.claveCorta'))
      return
    }
    if (passwordNueva !== confirmar) {
      setError(t('portal.clavesNoCoinciden'))
      return
    }
    setEnviando(true)
    try {
      const { access_token } = await cambiarPasswordPortal(passwordActual, passwordNueva)
      passwordCambiada(access_token)
      navigate('/portal', { replace: true })
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? (err.response?.data?.detail as string | undefined) : undefined
      setError(detalle || t('portal.errorCambiarClave'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full" style={{ maxWidth: 380 }}>
          <img
            src="/logo-yuda-importaciones.svg"
            alt="YUDA Importaciones"
            style={{ width: 200, height: 'auto', margin: '0 auto 20px', display: 'block' }}
          />
          <div className="text-center">
            <span
              className="inline-block rounded-full px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}
            >
              {t('portal.cambioClaveObligatorio')}
            </span>
            <h1 className="mt-4" style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>
              {t('portal.pongaSuClave')}
            </h1>
            <p style={{ fontSize: 14, color: 'var(--yuda-text-secondary)', marginTop: 4 }}>
              {t('portal.pongaSuClaveAyuda')}
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ marginTop: 28 }}>
            <label htmlFor="passwordActual" style={labelStyle}>
              {t('portal.claveActual')}
            </label>
            <input
              id="passwordActual"
              type="password"
              value={passwordActual}
              onChange={(e) => setPasswordActual(e.target.value)}
              autoComplete="current-password"
              required
              style={inputBase}
              className={inputClase}
            />

            <label htmlFor="passwordNueva" style={{ ...labelStyle, marginTop: 20 }}>
              {t('portal.claveNueva')}
            </label>
            <input
              id="passwordNueva"
              type="password"
              value={passwordNueva}
              onChange={(e) => setPasswordNueva(e.target.value)}
              autoComplete="new-password"
              required
              style={inputBase}
              className={inputClase}
            />

            <label htmlFor="confirmarClave" style={{ ...labelStyle, marginTop: 20 }}>
              {t('portal.confirmarClave')}
            </label>
            <input
              id="confirmarClave"
              type="password"
              value={confirmar}
              onChange={(e) => setConfirmar(e.target.value)}
              autoComplete="new-password"
              required
              style={inputBase}
              className={inputClase}
            />

            <button
              type="submit"
              disabled={enviando}
              className="mt-8 w-full rounded-lg bg-[var(--yuda-primary)] font-semibold text-white hover:bg-[var(--yuda-primary-dark)] disabled:opacity-60"
              style={{ height: 52, fontSize: 16 }}
            >
              {enviando ? t('portal.guardandoClave') : t('portal.guardarClave')}
            </button>

            {error && <p style={{ color: 'var(--yuda-error)', fontSize: 14, marginTop: 12 }}>{error}</p>}
          </form>
        </div>
      </div>
    </div>
  )
}

export default PortalCambiarPassword
