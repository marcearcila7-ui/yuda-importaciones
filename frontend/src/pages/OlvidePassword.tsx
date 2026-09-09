import { useState } from 'react'
import type { CSSProperties, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft } from 'lucide-react'
import { olvidePassword } from '../api/auth'

// font-size 16 evita el zoom automático en iOS
const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[var(--yuda-border)] bg-transparent focus:border-[var(--yuda-primary)] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: 'var(--yuda-text)', display: 'block' }

// Pide el correo de recuperación. El backend responde SIEMPRE el mismo mensaje
// genérico, exista o no esa cuenta, así que esta pantalla no distingue éxito de
// "ese correo no existe": mostrarlo distinto filtraría qué emails están registrados.
function OlvidePassword() {
  const { t } = useTranslation()
  const [email, setEmail] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [mensaje, setMensaje] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setEnviando(true)
    try {
      const texto = await olvidePassword(email)
      setMensaje(texto)
    } catch {
      setMensaje(t('login.errorOlvide'))
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
            {t('login.olvideTitulo')}
          </h1>
          <p style={{ fontSize: 14, color: 'var(--yuda-text-secondary)', marginTop: 8 }}>
            {t('login.olvideAyuda')}
          </p>
        </div>

        {mensaje ? (
          <p
            className="mt-6 rounded-lg px-3 py-3 text-center text-sm"
            style={{ backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }}
          >
            {mensaje}
          </p>
        ) : (
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

            <button
              type="submit"
              disabled={enviando}
              className="mt-8 w-full rounded-lg bg-[var(--yuda-primary)] font-semibold text-white hover:bg-[var(--yuda-primary-dark)] disabled:opacity-60"
              style={{ height: 52, fontSize: 16 }}
            >
              {enviando ? t('login.enviando') : t('login.olvideEnviar')}
            </button>
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

export default OlvidePassword
