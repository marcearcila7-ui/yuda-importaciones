import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ClipboardList, LogOut, Network, Package, Settings, Store, TrendingUp, Users, Wallet } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import NotificacionesBell from './NotificacionesBell'

// Logo circular YUDA (círculo azul con "Y" blanca)
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
              backgroundColor: activo ? 'var(--yuda-primary)' : 'transparent',
              color: activo ? 'var(--yuda-white)' : 'var(--yuda-text-secondary)',
              padding: '4px 10px',
              fontSize: 13,
              fontWeight: 600,
            }}
            onMouseEnter={(e) => {
              if (!activo) e.currentTarget.style.color = 'var(--yuda-primary)'
            }}
            onMouseLeave={(e) => {
              if (!activo) e.currentTarget.style.color = 'var(--yuda-text-secondary)'
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
  { to: '/dashboard', icono: <Package size={18} />, clave: 'cotizacion', roles: ['admin', 'vendedora'] },
  { to: '/clientes', icono: <Users size={18} />, clave: 'clientes', roles: ['admin', 'vendedora'] },
  { to: '/equipo', icono: <Network size={18} />, clave: 'equipo', roles: ['admin'] },
  { to: '/ventas', icono: <TrendingUp size={18} />, clave: 'ventas', roles: ['admin'] },
  { to: '/historial', icono: <ClipboardList size={18} />, clave: 'historial', roles: ['admin', 'contadora'] },
  { to: '/cuentas', icono: <Wallet size={18} />, clave: 'cuentas', roles: ['admin', 'contadora'] },
  { to: '/tiendas', icono: <Store size={18} />, clave: 'tiendas', roles: ['admin', 'contadora'] },
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
    <div className="flex h-full flex-col border-r border-gray-200" style={{ backgroundColor: 'var(--yuda-white)' }}>
      {/* Logo */}
      <div className="px-5 py-6">
        <img src="/logoyuda.png" alt="YUDA Importaciones" style={{ height: 36, width: 'auto' }} />
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
                backgroundColor: activo ? 'var(--yuda-primary)' : 'transparent',
                color: activo ? 'var(--yuda-white)' : 'var(--yuda-text)',
              }}
              onMouseEnter={(e) => {
                if (!activo) e.currentTarget.style.backgroundColor = 'var(--yuda-primary-soft)'
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
      <div className="border-t border-gray-200 px-4 py-4">
        <div className="mb-3">
          <SelectorIdioma />
        </div>
        <div className="flex items-center gap-3">
          <span
            className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full font-bold text-white"
            style={{ backgroundColor: 'var(--yuda-primary)' }}
          >
            {usuario?.nombre?.charAt(0).toUpperCase() ?? '?'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>{usuario?.nombre}</p>
            <p className="truncate text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {usuario?.rol ? t(`roles.${usuario.rol}`) : ''}
            </p>
          </div>
          {(rol === 'admin' || rol === 'vendedora' || rol === 'contadora') && <NotificacionesBell />}
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 flex w-full items-center justify-center gap-2 py-2 text-sm font-medium"
          style={{ backgroundColor: '#F3F4F6', color: 'var(--yuda-text)', borderRadius: 8 }}
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
