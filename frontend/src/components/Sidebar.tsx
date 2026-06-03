import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
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

interface ItemNav {
  to: string
  icono: string
  texto: string
  roles?: string[]
}

const LINKS: ItemNav[] = [
  { to: '/dashboard', icono: '📦', texto: 'Cotización' },
  { to: '/historial', icono: '📋', texto: 'Historial', roles: ['admin', 'contadora'] },
  { to: '/admin', icono: '⚙️', texto: 'Administración', roles: ['admin'] },
]

function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { usuario, logout } = useAuthStore()
  const [abierto, setAbierto] = useState(false)

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
              onClick={() => setAbierto(false)}
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
              <span className="text-base">{l.icono}</span>
              {l.texto}
            </Link>
          )
        })}
      </nav>

      {/* Usuario */}
      <div className="border-t border-white/10 px-4 py-4">
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
              {usuario?.rol}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          className="mt-3 flex w-full items-center justify-center gap-2 py-2 text-sm font-medium text-white"
          style={{ backgroundColor: '#1F1F1F', borderRadius: 8 }}
        >
          ⏏ Salir
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Sidebar fijo en desktop */}
      <aside className="hidden md:block" style={{ width: 240, flexShrink: 0 }}>
        <div className="fixed left-0 top-0 h-screen" style={{ width: 240 }}>
          {contenido}
        </div>
      </aside>

      {/* Top bar fija en mobile */}
      <div
        className="fixed left-0 right-0 top-0 z-30 flex items-center justify-between bg-white px-4 py-3 md:hidden"
        style={{ boxShadow: '0 1px 3px rgba(0,0,0,0.08)' }}
      >
        <div className="flex items-center gap-2">
          <LogoYuda size={28} />
          <span className="font-bold" style={{ color: '#0D0D0D' }}>
            YU·DA
          </span>
        </div>
        <button
          type="button"
          onClick={() => setAbierto(true)}
          className="text-2xl"
          style={{ color: '#0D0D0D' }}
          aria-label="Abrir menú"
        >
          ☰
        </button>
      </div>

      {/* Drawer mobile */}
      {abierto && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setAbierto(false)}
          />
          <div className="absolute left-0 top-0 h-full" style={{ width: 240 }}>
            {contenido}
          </div>
        </div>
      )}
    </>
  )
}

export default Sidebar
