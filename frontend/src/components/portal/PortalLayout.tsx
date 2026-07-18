import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { LogOut } from 'lucide-react'
import { usePortalStore } from '../../store/portalStore'

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

function SelectorIdioma() {
  const { i18n } = useTranslation()
  const cambiar = (code: string) => {
    i18n.changeLanguage(code)
    localStorage.setItem('yuda_idioma', code)
  }
  return (
    <div className="flex gap-1">
      {IDIOMAS.map((idi) => {
        const activo = i18n.language === idi.code
        return (
          <button
            key={idi.code}
            type="button"
            onClick={() => cambiar(idi.code)}
            style={{
              borderRadius: 8,
              backgroundColor: activo ? 'var(--yuda-primary)' : 'transparent',
              color: activo ? 'var(--yuda-white)' : 'var(--yuda-text-secondary)',
              padding: '8px 12px',
              fontSize: 14,
              fontWeight: 600,
            }}
          >
            {idi.label}
          </button>
        )
      })}
    </div>
  )
}

function PortalLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { cliente, logout } = usePortalStore()

  const salir = () => {
    logout()
    navigate('/portal/login')
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--yuda-bg)' }}>
      <Toaster position="top-right" />

      {/* Encabezado */}
      <header
        className="sticky top-0 z-30 flex items-center justify-between bg-white px-4 py-3 sm:px-8"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}
      >
        <img src="/logoyuda.png" alt="YUDA Importaciones" className="h-9 w-auto sm:h-12" />

        <div className="flex items-center gap-3">
          <SelectorIdioma />
          <span className="hidden max-w-[140px] truncate sm:inline" style={{ fontSize: 14, color: 'var(--yuda-text-secondary)' }}>
            {cliente?.nombre}
          </span>
          <button
            type="button"
            onClick={salir}
            className="flex items-center gap-1 rounded-lg px-2 py-1 text-sm font-medium"
            style={{ color: 'var(--yuda-text-secondary)' }}
          >
            <LogOut size={16} /> <span className="hidden sm:inline">{t('portal.salir')}</span>
          </button>
        </div>
      </header>

      <main className="mx-auto w-full px-4 py-6 sm:px-8" style={{ maxWidth: 1000 }}>
        {children}
      </main>
    </div>
  )
}

export default PortalLayout
