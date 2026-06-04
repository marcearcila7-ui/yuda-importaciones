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

export default portalClient
