import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import axios from 'axios'
import { ArrowLeft } from 'lucide-react'
import CampoPassword from '../components/CampoPassword'
import { resetPassword } from '../api/auth'

// Pantalla a la que llega el enlace del correo de recuperación (?token=...).
function ResetPassword() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''

  const [password, setPassword] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    if (password.length < 8) {
      setError(t('login.resetCorta'))
      return
    }
    if (password !== confirmar) {
      setError(t('login.resetNoCoincide'))
      return
    }
    setEnviando(true)
    try {
      await resetPassword(token, password)
      navigate('/login', { replace: true, state: { passwordActualizada: true } })
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      setError(typeof detalle === 'string' ? detalle : t('login.errorReset'))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-white px-6">
      <div className="w-full" style={{ maxWidth: 380 }}>
        <img
          src="/logoyuda.png"
          alt="YUDA Importaciones"
          style={{ height: 44, width: 'auto', margin: '0 auto 20px' }}
        />
        <div className="text-center">
          <h1 style={{ fontWeight: 700, fontSize: 26, color: 'var(--yuda-accent)' }}>
            {t('login.resetTitulo')}
          </h1>
          <p style={{ fontSize: 14, color: 'var(--yuda-text-secondary)', marginTop: 8 }}>
            {t('login.resetAyuda')}
          </p>
        </div>

        {!token ? (
          <p
            className="mt-6 rounded-lg px-3 py-3 text-center text-sm"
            style={{ backgroundColor: '#FEF2F2', color: 'var(--yuda-error-dark)' }}
          >
            {t('login.resetSinToken')}
          </p>
        ) : (
          <form onSubmit={handleSubmit} style={{ marginTop: 28 }}>
            <CampoPassword
              id="password"
              label={t('login.resetNueva')}
              value={password}
              onChange={setPassword}
              autoComplete="new-password"
              required
            />
            <CampoPassword
              id="confirmar"
              label={t('login.resetConfirmar')}
              value={confirmar}
              onChange={setConfirmar}
              autoComplete="new-password"
              required
              style={{ marginTop: 20 }}
            />

            <button
              type="submit"
              disabled={enviando}
              className="mt-8 w-full rounded-lg bg-[var(--yuda-primary)] font-semibold text-white hover:bg-[var(--yuda-primary-dark)] disabled:opacity-60"
              style={{ height: 52, fontSize: 16 }}
            >
              {enviando ? t('login.enviando') : t('login.resetGuardar')}
            </button>

            {error && (
              <p style={{ color: 'var(--yuda-error)', fontSize: 14, marginTop: 12 }}>{error}</p>
            )}
          </form>
        )}

        <Link
          to="/login"
          className="mt-6 flex items-center justify-center gap-1 text-sm font-medium"
          style={{ color: 'var(--yuda-text-secondary)' }}
        >
          <ArrowLeft size={15} /> {t('login.volverAIngresar')}
        </Link>
      </div>
    </div>
  )
}

export default ResetPassword
