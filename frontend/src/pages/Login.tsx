import { useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const inputStyle: CSSProperties = {
  fontSize: 16, // mínimo 16px para evitar el zoom automático en iOS
}

function Logo({ grande = false }: { grande?: boolean }) {
  return (
    <div className="text-center">
      <p
        style={{
          fontWeight: 800,
          fontSize: grande ? 48 : 32,
          color: grande ? '#FFFFFF' : '#0D0D0D',
          lineHeight: 1,
        }}
      >
        YU·DA
      </p>
      <p
        style={{
          fontSize: grande ? 14 : 11,
          letterSpacing: '0.3em',
          color: grande ? '#FFFFFF' : '#6B7280',
          marginTop: 6,
        }}
      >
        IMPORTACIONES
      </p>
    </div>
  )
}

function Login() {
  const navigate = useNavigate()
  const { login, isLoading, error } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    await login(email, password)
    // Si el login fue exitoso, el store guardó el token
    if (localStorage.getItem('yuda_token')) {
      navigate('/dashboard')
    }
  }

  return (
    <div className="flex min-h-screen">
      {/* Lado izquierdo (branding) — solo desktop */}
      <div
        className="hidden w-1/2 flex-col items-center justify-center p-10 md:flex"
        style={{ backgroundColor: '#4B52E8' }}
      >
        <Logo grande />
        <p className="mt-6 text-center text-lg font-medium text-white">
          Conectamos China con tu éxito
        </p>
      </div>

      {/* Lado derecho (formulario) */}
      <div className="flex w-full flex-col items-center justify-center bg-white px-6 md:w-1/2">
        <div className="w-full max-w-sm">
          {/* Logo pequeño arriba (visible sobre todo en mobile) */}
          <div className="mb-10 md:hidden">
            <Logo />
          </div>

          <h1 className="mb-8" style={{ fontWeight: 700, fontSize: 24, color: '#0D0D0D' }}>
            Iniciar sesión
          </h1>

          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                style={inputStyle}
                className="border-0 border-b-2 border-gray-200 bg-transparent py-2 focus:border-[#4B52E8] focus:outline-none"
              />
            </label>

            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              Contraseña
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                style={inputStyle}
                className="border-0 border-b-2 border-gray-200 bg-transparent py-2 focus:border-[#4B52E8] focus:outline-none"
              />
            </label>

            <button
              type="submit"
              disabled={isLoading}
              className="mt-2 w-full font-semibold text-white disabled:opacity-60"
              style={{ height: 52, backgroundColor: '#4B52E8', borderRadius: 8, fontSize: 16 }}
            >
              {isLoading ? 'Iniciando sesión...' : 'Ingresar'}
            </button>

            {error && (
              <p className="text-center text-sm" style={{ color: '#EF4444' }}>
                {error}
              </p>
            )}
          </form>
        </div>
      </div>
    </div>
  )
}

export default Login
