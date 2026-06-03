import { useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

// Estilos en línea para los requisitos críticos de mobile (iOS)
const inputStyle: CSSProperties = {
  fontSize: 16, // mínimo 16px para evitar el zoom automático en iOS
}

const botonStyle: CSSProperties = {
  minHeight: 48, // touch target adecuado
  fontSize: 16,
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
    <div
      className="flex min-h-screen flex-col items-center justify-center px-4"
      style={{ backgroundColor: '#1e3a5f' }}
    >
      <h1 className="mb-6 text-5xl font-bold tracking-wide text-white">YUDA</h1>

      <div className="w-full max-w-sm rounded-lg bg-white p-8 shadow-lg">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
              style={inputStyle}
              className="rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm text-gray-700">
            Contraseña
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              style={inputStyle}
              className="rounded border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none"
            />
          </label>

          <button
            type="submit"
            disabled={isLoading}
            style={botonStyle}
            className="mt-2 rounded bg-blue-700 px-4 font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
          >
            {isLoading ? 'Ingresando...' : 'Ingresar'}
          </button>

          {error && <p className="text-center text-sm text-red-600">{error}</p>}
        </form>
      </div>
    </div>
  )
}

export default Login
