import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './components/ProtectedRoute'
import Admin from './pages/Admin'
import Dashboard from './pages/Dashboard'
import Historial from './pages/Historial'
import Login from './pages/Login'
import { useAuthStore } from './store/authStore'

function App() {
  const initFromStorage = useAuthStore((state) => state.initFromStorage)

  // Restaura la sesión guardada al iniciar la app
  useEffect(() => {
    initFromStorage()
  }, [initFromStorage])

  return (
    <BrowserRouter>
      <Routes>
        {/* Ruta pública de login */}
        <Route path="/login" element={<Login />} />

        {/* Rutas protegidas (sin restricción de rol) */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
        </Route>

        {/* Solo administración */}
        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route path="/admin" element={<Admin />} />
        </Route>

        {/* Historial: admin y contadora */}
        <Route element={<ProtectedRoute roles={['admin', 'contadora']} />}>
          <Route path="/historial" element={<Historial />} />
        </Route>

        {/* Cualquier otra ruta redirige al dashboard */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
