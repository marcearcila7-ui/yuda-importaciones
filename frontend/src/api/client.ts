import axios from 'axios'

// Instancia axios base. En producción usa VITE_API_URL (frontend y backend en
// orígenes distintos); en desarrollo cae a la ruta relativa /api/v1 (proxeada por Vite).
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1',
})

// Auto-logout ante sesión vencida: si el backend responde 401 a una llamada
// autenticada, el token guardado ya no sirve. Lo limpiamos y mandamos al login
// (en vez de dejar la pantalla como si siguieras dentro y mostrar "No autenticado").
// Se excluye el propio /auth/login para no pisar el mensaje de "credenciales incorrectas".
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url: string = error.config?.url ?? ''
    const esLogin = url.includes('/auth/login')
    if (status === 401 && !esLogin && localStorage.getItem('yuda_token')) {
      localStorage.removeItem('yuda_token')
      localStorage.removeItem('yuda_usuario')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
