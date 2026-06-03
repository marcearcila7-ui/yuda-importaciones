import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ClipboardList, LogOut, Package, Settings } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

// Logo circular YUDA (círculo azul con "Y" blanca)
function LogoYuda({ size = 36 }: { size?: number }) {
  return (
    <span
      className="flex flex-shrink-0 items-center justify-center rounded-full font-extrabold text-white"
      style={{ width: size, height: size, backgroundColor: '#4B52E8', fontSize: size * 0.5 }}
    >
      Y
    </span>
  )
}

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

// Selector de idioma: ES | EN | 中文
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
              borderRadius: 6,
              backgroundColor: activo ? '#4B52E8' : 'transparent',
              color: activo ? '#FFFFFF' : '#9CA3AF',
              padding: '4px 10px',
              fontSize: 13,
              fontWeight: 600,
            }}
            onMouseEnter={(e) => {
              if (!activo) e.currentTarget.style.color = '#FFFFFF'
            }}
            onMouseLeave={(e) => {
              if (!activo) e.currentTarget.style.color = '#9CA3AF'
            }}
          >
            {idi.label}
          </button>
        )
      })}
    </div>
  )
}

interface ItemNav {
  to: string
  icono: ReactNode
  clave: string
  roles?: string[]
}

const LINKS: ItemNav[] = [
  { to: '/dashboard', icono: <Package size={18} />, clave: 'cotizacion' },
  { to: '/historial', icono: <ClipboardList size={18} />, clave: 'historial', roles: ['admin', 'contadora'] },
  { to: '/admin', icono: <Settings size={18} />, clave: 'administracion', roles: ['admin'] },
]

function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useTranslation()
  const { usuario, logout } = useAuthStore()

  const rol = usuario?.rol
  const linksVisibles = LINKS.filter((l) => !l.roles || (rol && l.roles.includes(rol)))

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Contenido del sidebar (compartido entre desktop y drawer mobile)
  const contenido = (
    <div className="flex h-full flex-col" style={{ backgroundColor: '#0D0D0D' }}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-6">
        <LogoYuda />
        <div>
          <p className="font-bold leading-none text-white" style={{ fontSize: 20 }}>
            YU·DA
          </p>
          <p style={{ color: '#9CA3AF', fontSize: 11 }}>Importaciones</p>
        </div>
      </div>

      {/* Navegación */}
      <nav className="flex flex-1 flex-col gap-1 px-3">
        {linksVisibles.map((l) => {
          const activo = location.pathname === l.to
          return (
            <Link
              key={l.to}
              to={l.to}
              className="flex items-center gap-3 px-3 py-3 text-sm font-medium transition-colors"
              style={{
                borderRadius: 8,
                backgroundColor: activo ? '#4B52E8' : 'transparent',
                color: activo ? '#FFFFFF' : '#9CA3AF',
              }}
              onMouseEnter={(e) => {
                if (!activo) e.currentTarget.style.backgroundColor = '#1F1F1F'
              }}
              onMouseLeave={(e) => {
                if (!activo) e.currentTarget.style.backgroundColor = 'transparent'
              }}
            >
              {l.icono}
              {t(`nav.${l.clave}`)}
            </Link>
          )
        })}
      </nav>

      {/* Selector de idioma + usuario */}
      <div className="border-t border-white/10 px-4 py-4">
        <div className="mb-3">
          <SelectorIdioma />
        </div>
        <div className="flex items-center gap-3">
          <span
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full font-bold text-white"
            style={{ backgroundColor: '#4B52E8' }}
          >
            {usuario?.nombre?.charAt(0).toUpperCase() ?? '?'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-white">{usuario?.nombre}</p>
            <p className="truncate text-xs" style={{ color: '#9CA3AF' }}>
              {usuario?.rol ? t(`roles.${usuario.rol}`) : ''}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 flex w-full items-center justify-center gap-2 py-2 text-sm font-medium text-white"
          style={{ backgroundColor: '#1F1F1F', borderRadius: 8 }}
        >
          <LogOut size={18} /> {t('nav.cerrarSesion')}
        </button>
      </div>
    </div>
  )

  // Sidebar fijo solo en desktop (en mobile se usan TopBar + BottomNav del Layout)
  return (
    <aside className="hidden md:block" style={{ width: 240, flexShrink: 0 }}>
      <div className="fixed left-0 top-0 h-screen" style={{ width: 240 }}>
        {contenido}
      </div>
    </aside>
  )
}

export default Sidebar
