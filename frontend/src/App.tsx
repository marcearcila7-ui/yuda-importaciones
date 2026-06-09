import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import PortalProtectedRoute from './components/portal/PortalProtectedRoute'
import Admin from './pages/Admin'
import Clientes from './pages/Clientes'
import CotizacionDetalle from './pages/CotizacionDetalle'
import Dashboard from './pages/Dashboard'
import Equipo from './pages/Equipo'
import Historial from './pages/Historial'
import Login from './pages/Login'
import PortalCotizaciones from './pages/portal/PortalCotizaciones'
import PortalDetalle from './pages/portal/PortalDetalle'
import PortalLogin from './pages/portal/PortalLogin'
import { useAuthStore } from './store/authStore'
import { usePortalStore } from './store/portalStore'

function App() {
  const initFromStorage = useAuthStore((state) => state.initFromStorage)
  const initPortal = usePortalStore((state) => state.initFromStorage)

  // Restaura las sesiones guardadas al iniciar la app (equipo y portal)
  useEffect(() => {
    initFromStorage()
    initPortal()
  }, [initFromStorage, initPortal])

  return (
    <BrowserRouter>
      <Routes>
        {/* ── Portal de clientes ── */}
        <Route path="/portal/login" element={<PortalLogin />} />
        <Route element={<PortalProtectedRoute />}>
          <Route path="/portal" element={<PortalCotizaciones />} />
          <Route path="/portal/cotizacion/:sesionId" element={<PortalDetalle />} />
        </Route>

        {/* ── Área del equipo ── */}
        <Route path="/login" element={<Login />} />

        {/* Rutas protegidas (sin restricción de rol) */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Layout><Dashboard /></Layout>} />
        </Route>

        {/* Clientes: admin y vendedora */}
        <Route element={<ProtectedRoute roles={['admin', 'vendedora']} />}>
          <Route path="/clientes" element={<Layout><Clientes /></Layout>} />
        </Route>

        {/* Solo administración */}
        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route path="/admin" element={<Layout><Admin /></Layout>} />
          <Route path="/equipo" element={<Layout><Equipo /></Layout>} />
        </Route>

        {/* Historial y detalle de cotización (solo lectura): admin y contadora */}
        <Route element={<ProtectedRoute roles={['admin', 'contadora']} />}>
          <Route path="/historial" element={<Layout><Historial /></Layout>} />
          <Route path="/cotizacion/:id" element={<Layout><CotizacionDetalle /></Layout>} />
        </Route>

        {/* Cualquier otra ruta redirige al dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
