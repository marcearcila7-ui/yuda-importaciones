import { useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../store/authStore'

// font-size 16 evita el zoom automático en iOS
const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[#E5E7EB] bg-transparent focus:border-[#4B52E8] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: '#374151', display: 'block' }

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

function Login() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { login, isLoading, error } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const cambiarIdioma = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('yuda_idioma', code)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await login(email, password)
    // Si el login fue exitoso, el store guardó el token
    if (localStorage.getItem('yuda_token')) {
      navigate('/dashboard')
    }
  }

  return (
    <div className="relative flex min-h-screen">
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
                backgroundColor: activo ? '#4B52E8' : '#EEF0FD',
                color: activo ? '#FFFFFF' : '#4B52E8',
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
      {/* Mitad izquierda (branding) — solo desktop */}
      <div
        className="hidden w-1/2 flex-col items-center justify-center md:flex"
        style={{ backgroundColor: '#4B52E8' }}
      >
        <p style={{ fontWeight: 800, fontSize: 56, color: '#FFFFFF', lineHeight: 1 }}>YU·DA</p>
        <p style={{ fontSize: 13, letterSpacing: 4, color: '#FFFFFF', marginTop: 8 }}>
          IMPORTACIONES
        </p>
        <div style={{ width: 40, height: 2, backgroundColor: '#FFFFFF', margin: '24px 0' }} />
        <p style={{ fontSize: 18, fontWeight: 400, color: '#FFFFFF' }}>
          {t('login.tagline')}
        </p>
        <p style={{ fontSize: 13, color: '#FFFFFF', opacity: 0.7, marginTop: 8 }}>
          义乌市与达贸易有限公司
        </p>
      </div>

      {/* Mitad derecha (formulario) */}
      <div className="flex w-full items-center justify-center bg-white px-6 md:w-1/2">
        <div className="w-full" style={{ maxWidth: 380 }}>
          {/* Logo pequeño arriba — solo mobile */}
          <p
            className="mb-8 text-center md:hidden"
            style={{ fontWeight: 800, fontSize: 28, color: '#4B52E8' }}
          >
            YU·DA
          </p>

          <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>{t('login.bienvenida')}</h1>
          <p style={{ fontSize: 14, color: '#6B7280', marginTop: 4 }}>
            {t('login.credenciales')}
          </p>

          <form onSubmit={handleSubmit} style={{ marginTop: 32 }}>
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

            {error && (
              <p style={{ color: '#EF4444', fontSize: 14, marginTop: 12 }}>{error}</p>
            )}
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
