import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

interface ProtectedRouteProps {
  roles?: string[]
}

function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const { token, usuario } = useAuthStore()

  // Sin token: a la pantalla de login
  if (!token) {
    return <Navigate to="/login" replace />
  }

  // Si se exigen roles y el del usuario no está en la lista: sin acceso
  if (roles && (!usuario || !roles.includes(usuario.rol))) {
    return <div>Sin acceso</div>
  }

  return <Outlet />
}

export default ProtectedRoute
