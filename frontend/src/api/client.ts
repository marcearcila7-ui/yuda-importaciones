import axios from 'axios'

// Instancia axios base. En producción usa VITE_API_URL (frontend y backend en
// orígenes distintos); en desarrollo cae a la ruta relativa /api/v1 (proxeada por Vite).
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1',
})

export default apiClient
