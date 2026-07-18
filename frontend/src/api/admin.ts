import apiClient from './client'
import type {
  ConfiguracionResponse,
  MetricasDashboard,
  MetricasVendedorasResponse,
  SesionHistorial,
  UsuarioAdmin,
  UsuarioCreate,
} from '../types/admin'
import type { EquipoResponse } from '../types/equipo'
import type { PanelVentas } from '../types/ventas'

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

// Panel de ventas de Marcela: filtra por rango de fechas y por vendedora.
export async function getPanelVentas(
  params: { desde?: string; hasta?: string; vendedora_id?: string } = {},
): Promise<PanelVentas> {
  const { data } = await apiClient.get<PanelVentas>('/admin/ventas', { params })
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
  limit?: number
  offset?: number
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

export async function getMetricasVendedoras(): Promise<MetricasVendedorasResponse> {
  const { data } = await apiClient.get<MetricasVendedorasResponse>('/admin/metricas-vendedoras')
  return data
}

export async function getEquipo(): Promise<EquipoResponse> {
  const { data } = await apiClient.get<EquipoResponse>('/admin/equipo')
  return data
}
