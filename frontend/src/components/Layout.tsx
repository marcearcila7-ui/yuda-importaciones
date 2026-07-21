import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { LogOut } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import BottomNav from './BottomNav'
import NotificacionesBell from './NotificacionesBell'
import Sidebar from './Sidebar'

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

// Selector de idioma compacto para la TopBar mobile
function SelectorIdiomaMobile() {
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
              borderRadius: 6,
              backgroundColor: activo ? 'var(--yuda-primary)' : 'transparent',
              color: activo ? 'var(--yuda-white)' : 'var(--yuda-text-secondary)',
              padding: '3px 8px',
              fontSize: 12,
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

export default function Layout({ children }: { children: ReactNode }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { usuario, logout } = useAuthStore()

  const cerrarSesion = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--yuda-bg)' }}>
      <Toaster position="top-right" />

      {/* Sidebar: solo desktop */}
      <Sidebar />

      {/* TopBar fija: solo mobile */}
      <div
        className="fixed left-0 right-0 top-0 z-30 flex items-center justify-between bg-white px-4 md:hidden"
        style={{ height: 56, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}
      >
        {/* En la barra compacta va el ícono (el logo completo no entra con los demás controles) */}
        <img src="/favicon.png" alt="YUDA" style={{ height: 30, width: 30 }} />
        <div className="flex items-center gap-2">
          <SelectorIdiomaMobile />
          {(usuario?.rol === 'admin' || usuario?.rol === 'vendedora' || usuario?.rol === 'contadora') && (
            <NotificacionesBell posicion="abajo" />
          )}
          <span className="max-w-[80px] truncate" style={{ fontSize: 14, color: 'var(--yuda-text-secondary)' }}>
            {usuario?.nombre}
          </span>
          <button
            type="button"
            onClick={cerrarSesion}
            aria-label={t('nav.cerrarSesion')}
            title={t('nav.cerrarSesion')}
            className="flex items-center justify-center rounded-lg"
            style={{ width: 40, height: 40, color: 'var(--yuda-error)' }}
          >
            <LogOut size={20} />
          </button>
        </div>
      </div>

      {/* Contenido: padding-top para la TopBar y padding-bottom para el BottomNav en mobile */}
      <main className="flex-1 overflow-y-auto px-4 pb-20 pt-16 md:p-8">{children}</main>

      {/* BottomNav: solo mobile */}
      <BottomNav />
    </div>
  )
}
