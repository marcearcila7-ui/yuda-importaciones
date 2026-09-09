import { useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

// font-size 16 evita el zoom automático en iOS
const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[var(--yuda-border)] bg-transparent focus:border-[var(--yuda-primary)] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: 'var(--yuda-text)', display: 'block' }

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

function Login() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { login, isLoading, error, token, usuario } = useAuthStore()
  // Si el usuario llego aca porque se le vencio la sesion, hay que decirselo:
  // de otro modo parece que la app lo hubiera echado sin motivo.
  const [sesionVencida] = useState(() => {
    const vencida = sessionStorage.getItem('yuda_sesion_vencida') === '1'
    if (vencida) sessionStorage.removeItem('yuda_sesion_vencida')
    return vencida
  })
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // Escriben con el pulgar y presión de tiempo (en el mercado, frente al
  // cliente): poder ver lo que tipearon evita errores de dedo sin darse cuenta.
  const [verPassword, setVerPassword] = useState(false)

  // La sesión vive en un token guardado, no en qué pantalla se está viendo: si el
  // gesto de "volver" del celular trae de regreso a esta URL con el token todavía
  // vigente (nadie cerró sesión, solo cambió de pantalla), mostrar el formulario
  // era engañoso, parecía pedir la contraseña de nuevo y en realidad no la pedía
  // (al avanzar quedaba adentro igual). Si ya hay sesión, se salta directo.
  if (token && usuario && !sesionVencida) {
    return <Navigate to={usuario.rol === 'contadora' ? '/historial' : '/dashboard'} replace />
  }

  const cambiarIdioma = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('yuda_idioma', code)
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    const ok = await login(email, password)
    if (ok) {
      // La contadora no crea cotizaciones: su inicio es el historial.
      // replace: true para que el login no quede en el historial como destino de
      // "volver" (ver también el redirect de arriba si igual se llega acá logueada).
      const rol = useAuthStore.getState().usuario?.rol
      navigate(rol === 'contadora' ? '/historial' : '/dashboard', { replace: true })
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-white px-6">
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
      {/* Formulario centrado (todo blanco) */}
      <div className="w-full" style={{ maxWidth: 380 }}>
          {/* Logo + distintivo del equipo, centrado */}
          <img
            src="/logoyuda.png"
            alt="YUDA Importaciones"
            style={{ height: 44, width: 'auto', margin: '0 auto 20px' }}
          />
          {sesionVencida && (
            <p
              className="mb-4 rounded-lg px-3 py-2 text-sm"
              style={{ backgroundColor: '#FFFBEB', color: '#92400E' }}
            >
              {t('login.sesionVencida')}
            </p>
          )}
          <div className="text-center">
            <span
              className="inline-block rounded-full px-3 py-1 text-xs font-semibold"
              style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
            >
              {t('login.accesoEquipo')}
            </span>
            <h1 className="mt-4" style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>
              {t('login.bienvenida')}
            </h1>
            <p style={{ fontSize: 14, color: 'var(--yuda-text-secondary)', marginTop: 4 }}>
              {t('login.credenciales')}
            </p>
          </div>

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

            <p className="mt-2 text-right text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('login.olvideContrasena')}
            </p>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-8 w-full rounded-lg bg-[var(--yuda-primary)] font-semibold text-white hover:bg-[var(--yuda-primary-dark)] disabled:opacity-60"
              style={{ height: 52, fontSize: 16 }}
            >
              {isLoading ? t('login.ingresando') : t('login.ingresar')}
            </button>

            {error && (
              <p style={{ color: 'var(--yuda-error)', fontSize: 14, marginTop: 12 }}>{error}</p>
            )}
          </form>
      </div>
    </div>
  )
}

export default Login
