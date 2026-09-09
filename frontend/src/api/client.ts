import axios from 'axios'

// Instancia axios base. En producción usa VITE_API_URL (frontend y backend en
// orígenes distintos); en desarrollo cae a la ruta relativa /api/v1 (proxeada por Vite).
//
// timeout: sin esto axios espera para siempre (default 0). En el mercado, con
// handoffs de antena o zonas muertas, una conexión se queda "colgada" sin fallar
// limpio: ni resuelve ni rechaza. Como TODO el manejo de errores de la app depende
// de que la promesa se resuelva o rechace, eso dejaba botones en "Ingresando…",
// "Generando…" o "Guardando…" trabados para siempre, sin mensaje ni forma de
// reintentar salvo recargar. Las llamadas que de verdad tardan (subir fotos,
// generar documentos) ya fijan su propio timeout más largo por request, que
// pisa este default.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1',
  timeout: 20_000,
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
      // Se deja dicho POR QUE se cerro la sesion. El redirect recarga la pagina y
      // se lleva puesto cualquier aviso en pantalla, asi que el mensaje viaja por
      // aca y lo muestra el login. Sin esto la vendedora solo veia el error crudo
      // del servidor ("No autenticado") y no entendia que tenia que volver a entrar.
      sessionStorage.setItem('yuda_sesion_vencida', '1')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default apiClient
