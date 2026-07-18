import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from 'react'

// Botón reusable de YUDA. Centraliza colores (vía tokens) y tamaños para que
// todos los botones se vean igual y un cambio de marca sea un solo lugar.
type Variant = 'primary' | 'success' | 'dark' | 'danger' | 'ghost'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  fullWidth?: boolean
  children: ReactNode
}

const VARIANTES: Record<Variant, CSSProperties> = {
  primary: { backgroundColor: 'var(--yuda-primary)', color: 'var(--yuda-white)' },
  success: { backgroundColor: 'var(--yuda-success)', color: 'var(--yuda-white)' },
  dark: { backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' },
  danger: { backgroundColor: 'var(--yuda-error)', color: 'var(--yuda-white)' },
  ghost: {
    backgroundColor: 'transparent',
    color: 'var(--yuda-text-secondary)',
    border: '1px solid var(--yuda-border)',
  },
}

// fontSize >= 16 en md/lg evita el zoom automático de iOS al enfocar.
const TAMANOS: Record<Size, CSSProperties> = {
  sm: { minHeight: 36, fontSize: 14, padding: '0 12px' },
  md: { minHeight: 44, fontSize: 16, padding: '0 16px' },
  lg: { minHeight: 48, fontSize: 16, padding: '0 20px' },
}

function Button({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  children,
  className = '',
  style,
  type = 'button',
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-opacity disabled:opacity-60 ${
        fullWidth ? 'w-full' : ''
      } ${className}`}
      style={{ ...VARIANTES[variant], ...TAMANOS[size], ...style }}
      {...rest}
    >
      {children}
    </button>
  )
}

export default Button
