import { useEffect, useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { usePortalStore } from '../../store/portalStore'

const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[#E5E7EB] bg-transparent focus:border-[#4B52E8] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: '#374151', display: 'block' }

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

  // Si ya hay sesión de cliente, ir directo al portal
  useEffect(() => {
    if (token) navigate('/portal', { replace: true })
  }, [token, navigate])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    const ok = await login(email.trim().toLowerCase(), password)
    if (ok) {
      navigate('/portal')
    }
  }

  const cambiarIdioma = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('yuda_idioma', code)
  }

  return (
    <div className="flex min-h-screen flex-col bg-white">
      {/* Selector de idioma arriba */}
      <div className="flex justify-end gap-1 p-4">
        {IDIOMAS.map((idi) => {
          const activo = i18n.language === idi.code
          return (
            <button
              key={idi.code}
              type="button"
              onClick={() => cambiarIdioma(idi.code)}
              style={{
                borderRadius: 6,
                backgroundColor: activo ? '#4B52E8' : 'transparent',
                color: activo ? '#FFFFFF' : '#6B7280',
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

      <div className="flex flex-1 items-center justify-center px-6">
        <div className="w-full" style={{ maxWidth: 380 }}>
          <img
            src="/logoyuda.png"
            alt="YUDA Importaciones"
            style={{ height: 48, width: 'auto', margin: '0 auto 20px' }}
          />
          <div className="text-center">
            <span
              className="inline-block rounded-full px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: '#D1FAE5', color: '#047857' }}
            >
              {t('portal.accesoPortal')}
            </span>
            <h1 className="mt-4" style={{ fontWeight: 700, fontSize: 26, color: '#0D0D0D' }}>
              {t('portal.bienvenida')}
            </h1>
            <p style={{ fontSize: 14, color: '#6B7280', marginTop: 4 }}>{t('portal.credenciales')}</p>
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
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              style={inputBase}
              className={inputClase}
            />

            <button
              type="submit"
              disabled={isLoading}
              className="mt-8 w-full rounded-lg bg-[#4B52E8] font-semibold text-white hover:bg-[#3840C7] disabled:opacity-60"
              style={{ height: 52, fontSize: 16 }}
            >
              {isLoading ? t('login.ingresando') : t('login.ingresar')}
            </button>

            {error && <p style={{ color: '#EF4444', fontSize: 14, marginTop: 12 }}>{error}</p>}
          </form>
        </div>
      </div>
    </div>
  )
}

export default PortalLogin
