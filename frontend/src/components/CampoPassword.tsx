import { useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff } from 'lucide-react'

// font-size 16 evita el zoom automático en iOS
const inputBase: CSSProperties = { padding: '12px 0', fontSize: 16 }
const inputClase =
  'w-full border-0 border-b border-[var(--yuda-border)] bg-transparent focus:border-[var(--yuda-primary)] focus:outline-none'
const labelStyle: CSSProperties = { fontSize: 14, fontWeight: 500, color: 'var(--yuda-text)', display: 'block' }

// Campo de contraseña con ojito para mostrar/ocultar. Escriben con el pulgar y
// presión de tiempo (en el mercado, frente al cliente): poder ver lo que
// tipearon evita errores de dedo sin darse cuenta. Usado en Login y en elegir
// una contraseña nueva (recuperar contraseña).
function CampoPassword({
  id,
  label,
  value,
  onChange,
  autoComplete,
  required,
  style,
}: {
  id: string
  label: string
  value: string
  onChange: (v: string) => void
  autoComplete?: string
  required?: boolean
  style?: CSSProperties
}) {
  const { t } = useTranslation()
  const [verPassword, setVerPassword] = useState(false)

  return (
    <div style={style}>
      <label htmlFor={id} style={labelStyle}>
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={verPassword ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          required={required}
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
    </div>
  )
}

export default CampoPassword
