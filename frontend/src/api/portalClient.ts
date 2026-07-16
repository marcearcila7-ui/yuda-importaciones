import axios from 'axios'

// Instancia axios independiente para el portal de clientes.
// Usa su propio token (yuda_portal_token) para no mezclarse con el del equipo.
const portalClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1',
})

portalClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('yuda_portal_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-logout ante sesión vencida del cliente: si el backend responde 401 a una
// llamada autenticada, el token del portal ya no sirve. Lo limpiamos y mandamos
// al login del portal (en vez de dejar la pantalla colgada como si siguiera dentro).
// Se excluye /portal/login para no pisar el mensaje de "credenciales incorrectas".
portalClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url: string = error.config?.url ?? ''
    const esLogin = url.includes('/portal/login')
    if (status === 401 && !esLogin && localStorage.getItem('yuda_portal_token')) {
      localStorage.removeItem('yuda_portal_token')
      localStorage.removeItem('yuda_portal_cliente')
      if (!window.location.pathname.startsWith('/portal/login')) {
        window.location.href = '/portal/login'
      }
    }
    return Promise.reject(error)
  },
)

export default portalClient
