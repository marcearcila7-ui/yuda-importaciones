import { Navigate, Outlet } from 'react-router-dom'
import { usePortalStore } from '../../store/portalStore'

// Protege las rutas del portal: sin token de cliente, redirige al login del portal
function PortalProtectedRoute() {
  const { token } = usePortalStore()
  if (!token) {
    return <Navigate to="/portal/login" replace />
  }
  return <Outlet />
}

export default PortalProtectedRoute
