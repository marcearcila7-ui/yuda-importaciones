import { useEffect, useRef, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff } from 'lucide-react'
import HCaptcha from '@hcaptcha/react-hcaptcha'
import { usePortalStore } from '../../store/portalStore'

const HCAPTCHA_SITE_KEY = import.meta.env.VITE_HCAPTCHA_SITE_KEY as string | undefined

const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[var(--yuda-border)] bg-transparent focus:border-[var(--yuda-primary)] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: 'var(--yuda-text)', display: 'block' }

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

function PortalLogin() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { login, isLoading, error, token, clearError } = usePortalStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [captchaToken, setCaptchaToken] = useState<string | null>(null)
  const captchaRef = useRef<HCaptcha>(null)
  const [verPassword, setVerPassword] = useState(false)

  // Si ya hay sesión de cliente, ir directo al portal
  useEffect(() => {
    if (token) navigate('/portal', { replace: true })
  }, [token, navigate])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    const ok = await login(email.trim().toLowerCase(), password, captchaToken)
    if (ok) {
      navigate('/portal')
    } else {
      captchaRef.current?.resetCaptcha()
      setCaptchaToken(null)
    }
  }

  const cambiarIdioma = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('yuda_idioma', code)
  }

  return (
    <div
      className="relative flex min-h-screen items-center justify-center overflow-hidden px-6"
      style={{ backgroundColor: 'var(--yuda-bg)' }}
    >
      <div className="tapiz" />
      {/* Selector de idioma: visible siempre, arriba a la derecha */}
      <div className="absolute right-4 top-4 z-20 flex gap-1">
        {IDIOMAS.map((idi) => {
          const activo = i18n.language === idi.code
          return (
            <button
              key={idi.code}
              type="button"
              onClick={() => cambiarIdioma(idi.code)}
              style={{
                borderRadius: 6,
                backgroundColor: activo ? 'var(--yuda-primary)' : 'var(--yuda-primary-soft)',
                color: activo ? 'var(--yuda-white)' : 'var(--yuda-primary)',
                padding: '4px 10px',
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {idi.label}
            </button>
          )
        })}
      </div>

      <div
        className="relative z-10 w-full"
        style={{
          maxWidth: 420,
          backgroundColor: 'var(--yuda-card)',
          borderRadius: 20,
          boxShadow: '0 12px 40px rgba(28,30,51,0.10)',
          padding: '44px 40px',
        }}
      >
          <img
            src="/logo-yuda-importaciones.svg"
            alt="YUDA Importaciones"
            style={{ width: 200, height: 'auto', margin: '0 auto 20px', display: 'block' }}
          />
          <div className="text-center">
            <span
              className="inline-block rounded-full px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
            >
              {t('portal.accesoPortal')}
            </span>
            <h1 className="mt-4" style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>
              {t('login.bienvenida')}
            </h1>
            <p style={{ fontSize: 14, color: 'var(--yuda-text-secondary)', marginTop: 4 }}>{t('login.credenciales')}</p>
          </div>

          <form onSubmit={handleSubmit} style={{ marginTop: 28 }}>
            <label htmlFor="email" style={labelStyle}>
              {t('login.email')}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              style={inputBase}
              className={inputClase}
            />

            <label htmlFor="password" style={{ ...labelStyle, marginTop: 20 }}>
              {t('login.contrasena')}
            </label>
            <div className="relative">
              <input
                id="password"
                type={verPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                style={{ ...inputBase, paddingRight: 32 }}
                className={inputClase}
              />
              <button
                type="button"
                onClick={() => setVerPassword((v) => !v)}
                aria-label={t(verPassword ? 'login.ocultarContrasena' : 'login.verContrasena')}
                className="absolute bottom-2 right-0 flex items-center justify-center"
                style={{ width: 28, height: 28, color: 'var(--yuda-text-secondary)' }}
              >
                {verPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {HCAPTCHA_SITE_KEY && (
              <div className="mt-4 flex justify-center">
                <HCaptcha
                  ref={captchaRef}
                  sitekey={HCAPTCHA_SITE_KEY}
                  onVerify={setCaptchaToken}
                  onExpire={() => setCaptchaToken(null)}
                />
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || (!!HCAPTCHA_SITE_KEY && !captchaToken)}
              className="mt-8 w-full rounded-lg bg-[var(--yuda-primary)] font-semibold text-white hover:bg-[var(--yuda-primary-dark)] disabled:opacity-60"
              style={{ height: 52, fontSize: 16 }}
            >
              {isLoading ? t('login.ingresando') : t('login.ingresar')}
            </button>

            {error && <p style={{ color: 'var(--yuda-error)', fontSize: 14, marginTop: 12 }}>{error}</p>}
          </form>
      </div>
    </div>
  )
}

export default PortalLogin
