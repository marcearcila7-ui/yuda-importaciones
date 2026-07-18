import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ConfirmDialog from './components/ConfirmDialog'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import PortalProtectedRoute from './components/portal/PortalProtectedRoute'
// Camino común del equipo: se cargan de entrada.
import Clientes from './pages/Clientes'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import { useAuthStore } from './store/authStore'
import { usePortalStore } from './store/portalStore'

// Páginas de admin y del portal: se cargan bajo demanda (code-splitting) para
// aligerar el bundle inicial de las vendedoras.
const Admin = lazy(() => import('./pages/Admin'))
const CotizacionDetalle = lazy(() => import('./pages/CotizacionDetalle'))
const Equipo = lazy(() => import('./pages/Equipo'))
const Historial = lazy(() => import('./pages/Historial'))
const Ventas = lazy(() => import('./pages/Ventas'))
const PortalCotizaciones = lazy(() => import('./pages/portal/PortalCotizaciones'))
const PortalDetalle = lazy(() => import('./pages/portal/PortalDetalle'))
const PortalLogin = lazy(() => import('./pages/portal/PortalLogin'))

function Cargando() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6B7280' }}>
      Cargando…
    </div>
  )
}

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
      <ConfirmDialog />
      <Suspense fallback={<Cargando />}>
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
          <Route path="/ventas" element={<Layout><Ventas /></Layout>} />
        </Route>

        {/* Historial: solo admin y contadora */}
        <Route element={<ProtectedRoute roles={['admin', 'contadora']} />}>
          <Route path="/historial" element={<Layout><Historial /></Layout>} />
        </Route>

        {/* Detalle de cotización (solo lectura): admin, contadora y la vendedora
            dueña. El backend limita los datos a las cotizaciones propias. */}
        <Route element={<ProtectedRoute roles={['admin', 'contadora', 'vendedora']} />}>
          <Route path="/cotizacion/:id" element={<Layout><CotizacionDetalle /></Layout>} />
        </Route>

        {/* Cualquier otra ruta redirige al dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
      </Suspense>
    </BrowserRouter>
  )
}

export default App
