import type { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ClipboardList, Network, Package, Settings, Users } from 'lucide-react'
import { useAuthStore } from '../store/authStore'

interface ItemNav {
  to: string
  icono: ReactNode
  i18nKey: string
  roles?: string[]
}

const ITEMS: ItemNav[] = [
  { to: '/dashboard', icono: <Package size={24} />, i18nKey: 'nav.cotizacion', roles: ['admin', 'vendedora'] },
  { to: '/clientes', icono: <Users size={24} />, i18nKey: 'nav.clientes', roles: ['admin', 'vendedora'] },
  { to: '/equipo', icono: <Network size={24} />, i18nKey: 'nav.equipo', roles: ['admin'] },
  { to: '/historial', icono: <ClipboardList size={24} />, i18nKey: 'nav.historial', roles: ['admin', 'contadora'] },
  { to: '/admin', icono: <Settings size={24} />, i18nKey: 'nav.admin', roles: ['admin'] },
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
              backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'transparent',
              color: activo ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
              textDecoration: 'none',
            }}
          >
            {item.icono}
            <span style={{ fontSize: 10, fontWeight: 500 }}>{t(item.i18nKey)}</span>
          </Link>
        )
      })}
    </nav>
  )
}

export default BottomNav
