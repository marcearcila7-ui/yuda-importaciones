import apiClient from './client'
import type {
  ComisionesReporte,
  EmpleadaResumen,
  PedidoTienda,
  PedidoTiendaCreate,
} from '../types/tienda'

export async function getPedidosTienda(): Promise<PedidoTienda[]> {
  const { data } = await apiClient.get<PedidoTienda[]>('/tiendas/pedidos')
  return data
}

export async function crearPedidoTienda(datos: PedidoTiendaCreate): Promise<PedidoTienda> {
  const { data } = await apiClient.post<PedidoTienda>('/tiendas/pedidos', datos)
  return data
}

export async function actualizarPedidoTienda(
  id: string,
  datos: Partial<PedidoTiendaCreate>,
): Promise<PedidoTienda> {
  const { data } = await apiClient.patch<PedidoTienda>(`/tiendas/pedidos/${id}`, datos)
  return data
}

export async function eliminarPedidoTienda(id: string): Promise<void> {
  await apiClient.delete(`/tiendas/pedidos/${id}`)
}

export async function getEmpleadas(): Promise<EmpleadaResumen[]> {
  const { data } = await apiClient.get<EmpleadaResumen[]>('/tiendas/empleadas')
  return data
}

export async function getComisiones(
  desde?: string | null,
  hasta?: string | null,
): Promise<ComisionesReporte> {
  const params: Record<string, string> = {}
  if (desde) params.desde = desde
  if (hasta) params.hasta = hasta
  const { data } = await apiClient.get<ComisionesReporte>('/tiendas/comisiones', { params })
  return data
}
