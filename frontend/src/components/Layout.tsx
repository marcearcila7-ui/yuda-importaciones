import type { ReactNode } from 'react'
import { Toaster } from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../store/authStore'
import BottomNav from './BottomNav'
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
              backgroundColor: activo ? '#4B52E8' : 'transparent',
              color: activo ? '#FFFFFF' : '#9CA3AF',
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
  const { usuario } = useAuthStore()

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#F5F5F0' }}>
      <Toaster position="top-right" />

      {/* Sidebar: solo desktop */}
      <Sidebar />

      {/* TopBar fija: solo mobile */}
      <div
        className="fixed left-0 right-0 top-0 z-30 flex items-center justify-between bg-white px-4 md:hidden"
        style={{ height: 56, boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}
      >
        <span style={{ fontWeight: 800, fontSize: 20, color: '#4B52E8' }}>YU·DA</span>
        <div className="flex items-center gap-3">
          <SelectorIdiomaMobile />
          <span className="max-w-[110px] truncate" style={{ fontSize: 14, color: '#6B7280' }}>
            {usuario?.nombre}
          </span>
        </div>
      </div>

      {/* Contenido: padding-top para la TopBar y padding-bottom para el BottomNav en mobile */}
      <main className="flex-1 overflow-y-auto px-4 pb-20 pt-16 md:p-8">{children}</main>

      {/* BottomNav: solo mobile */}
      <BottomNav />
    </div>
  )
}
