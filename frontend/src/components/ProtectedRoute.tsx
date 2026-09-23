import { Link, Navigate, Outlet } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ShieldAlert } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import Layout from './Layout'

interface ProtectedRouteProps {
  roles?: string[]
}

// A dónde mandar a alguien que no tiene acceso a la ruta que pidió: el primer
// destino que sí puede ver, igual que el orden del Sidebar (para contadora,
// eso es Historial; para cualquier otro rol del equipo, el dashboard).
function destinoSegunRol(rol: string | undefined): string {
  return rol === 'contadora' ? '/historial' : '/dashboard'
}

function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const { t } = useTranslation()
  const { token, usuario } = useAuthStore()

  // Sin token: a la pantalla de login
  if (!token) {
    return <Navigate to="/login" replace />
  }

  // Si se exigen roles y el del usuario no está en la lista: sin acceso
  if (roles && (!usuario || !roles.includes(usuario.rol))) {
    return (
      <Layout>
        <div className="card mx-auto flex max-w-md flex-col items-center gap-3 py-10 text-center">
          <ShieldAlert size={40} color="var(--yuda-warning)" />
          <h1 style={{ fontWeight: 700, fontSize: 20, color: 'var(--yuda-accent)' }}>
            {t('common.sinAccesoTitulo')}
          </h1>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('common.sinAccesoAyuda')}
          </p>
          <Link
            to={destinoSegunRol(usuario?.rol)}
            className="mt-2 rounded-lg px-4 py-2 text-sm font-semibold text-white"
            style={{ backgroundColor: 'var(--yuda-primary)' }}
          >
            {t('common.volver')}
          </Link>
        </div>
      </Layout>
    )
  }

  return <Outlet />
}

export default ProtectedRoute
