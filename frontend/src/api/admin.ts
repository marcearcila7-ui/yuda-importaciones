import apiClient from './client'
import type {
  ConfiguracionResponse,
  MetricasDashboard,
  SesionHistorial,
  UsuarioAdmin,
  UsuarioCreate,
} from '../types/admin'

// Adjunta el token de localStorage en cada request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('yuda_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function getUsuarios(): Promise<UsuarioAdmin[]> {
  const { data } = await apiClient.get<UsuarioAdmin[]>('/admin/usuarios')
  return data
}

export async function crearUsuario(datos: UsuarioCreate): Promise<UsuarioAdmin> {
  const { data } = await apiClient.post<UsuarioAdmin>('/admin/usuarios', datos)
  return data
}

export async function actualizarUsuario(
  id: string,
  datos: Partial<{ nombre: string; rol: string; activo: boolean }>,
): Promise<UsuarioAdmin> {
  const { data } = await apiClient.patch<UsuarioAdmin>(`/admin/usuarios/${id}`, datos)
  return data
}

export async function resetPassword(id: string, nueva_password: string): Promise<void> {
  await apiClient.post(`/admin/usuarios/${id}/reset-password`, { nueva_password })
}

export async function getConfiguracion(): Promise<ConfiguracionResponse> {
  const { data } = await apiClient.get<ConfiguracionResponse>('/admin/configuracion')
  return data
}

export async function actualizarConfiguracion(
  tipo_cambio_usd: number,
): Promise<ConfiguracionResponse> {
  const { data } = await apiClient.patch<ConfiguracionResponse>('/admin/configuracion', {
    tipo_cambio_usd,
  })
  return data
}

export async function getHistorial(filtros?: {
  fecha_desde?: string
  fecha_hasta?: string
  nombre_cliente?: string
}): Promise<SesionHistorial[]> {
  const { data } = await apiClient.get<SesionHistorial[]>('/historial/sesiones', {
    params: filtros,
  })
  return data
}

export async function getMetricas(): Promise<MetricasDashboard> {
  const { data } = await apiClient.get<MetricasDashboard>('/admin/metricas')
  return data
}
