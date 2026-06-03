import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '../store/authStore'

interface ItemNav {
  to: string
  icono: string
  i18nKey: string
  roles?: string[]
}

const ITEMS: ItemNav[] = [
  { to: '/dashboard', icono: '📦', i18nKey: 'nav.cotizacion' },
  { to: '/historial', icono: '📋', i18nKey: 'nav.historial', roles: ['admin', 'contadora'] },
  { to: '/admin', icono: '⚙️', i18nKey: 'nav.admin', roles: ['admin'] },
]

// Barra de navegación inferior, solo visible en mobile
function BottomNav() {
  const location = useLocation()
  const { t } = useTranslation()
  const { usuario } = useAuthStore()

  const rol = usuario?.rol
  const visibles = ITEMS.filter((i) => !i.roles || (rol && i.roles.includes(rol)))

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-30 flex items-stretch justify-around bg-white md:hidden"
      style={{ height: 64, boxShadow: '0 -1px 6px rgba(0,0,0,0.08)' }}
    >
      {visibles.map((item) => {
        const activo = location.pathname === item.to
        return (
          <Link
            key={item.to}
            to={item.to}
            className="mx-1 my-2 flex flex-1 flex-col items-center justify-center gap-1"
            style={{
              borderRadius: 12,
              backgroundColor: activo ? '#EEF0FD' : 'transparent',
              color: activo ? '#4B52E8' : '#9CA3AF',
              textDecoration: 'none',
            }}
          >
            <span style={{ fontSize: 24, lineHeight: 1 }}>{item.icono}</span>
            <span style={{ fontSize: 10, fontWeight: 500 }}>{t(item.i18nKey)}</span>
          </Link>
        )
      })}
    </nav>
  )
}

export default BottomNav
