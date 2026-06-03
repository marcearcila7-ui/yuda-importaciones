import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

function Navbar() {
  const navigate = useNavigate()
  const { usuario, logout } = useAuthStore()
  const [abierto, setAbierto] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const rol = usuario?.rol
  const puedeHistorial = rol === 'admin' || rol === 'contadora'
  const puedeAdmin = rol === 'admin'

  // Links según el rol
  const links = (
    <>
      <Link to="/dashboard" className="px-2 py-2 text-sm font-medium text-gray-700 hover:text-blue-700">
        Cotización
      </Link>
      {puedeHistorial && (
        <Link to="/historial" className="px-2 py-2 text-sm font-medium text-gray-700 hover:text-blue-700">
          Historial
        </Link>
      )}
      {puedeAdmin && (
        <Link to="/admin" className="px-2 py-2 text-sm font-medium text-gray-700 hover:text-blue-700">
          Administración
        </Link>
      )}
    </>
  )

  return (
    <header className="border-b border-gray-200 bg-white">
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-6">
          <span className="text-2xl font-bold text-gray-800">YUDA</span>
          {/* Links horizontales en pantallas medianas o más grandes */}
          <nav className="hidden items-center gap-2 sm:flex">{links}</nav>
        </div>

        <div className="flex items-center gap-4">
          <span className="hidden text-sm text-gray-700 sm:inline">
            {usuario?.nombre} ({usuario?.rol})
          </span>
          <button
            onClick={handleLogout}
            className="rounded bg-gray-200 px-3 py-1 text-sm font-medium text-gray-800 hover:bg-gray-300"
          >
            Cerrar sesión
          </button>
          {/* Botón hamburguesa solo en mobile */}
          <button
            onClick={() => setAbierto((v) => !v)}
            className="text-2xl text-gray-700 sm:hidden"
            aria-label="Menú"
          >
            ☰
          </button>
        </div>
      </div>

      {/* Menú colapsable en mobile */}
      {abierto && (
        <nav className="flex flex-col border-t border-gray-100 px-6 py-2 sm:hidden">
          <span className="py-1 text-sm text-gray-500">
            {usuario?.nombre} ({usuario?.rol})
          </span>
          {links}
        </nav>
      )}
    </header>
  )
}

export default Navbar
