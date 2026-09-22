import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { usePortalStore } from '../../store/portalStore'

// Protege las rutas del portal: sin token de cliente, redirige al login del
// portal. Si todavía tiene la clave de plantilla de la importación de Yuda
// Contable, lo manda a cambiarla antes de dejarlo ver nada más.
function PortalProtectedRoute() {
  const { token, cliente } = usePortalStore()
  const location = useLocation()
  if (!token) {
    return <Navigate to="/portal/login" replace />
  }
  if (cliente?.debe_cambiar_password && location.pathname !== '/portal/cambiar-clave') {
    return <Navigate to="/portal/cambiar-clave" replace />
  }
  return <Outlet />
}

export default PortalProtectedRoute
