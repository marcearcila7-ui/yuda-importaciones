import apiClient from './client'
import type { EstadoCuenta, MovimientoCreate } from '../types/cuenta'

export async function getEstadoCuenta(cliente_id: string): Promise<EstadoCuenta> {
  const { data } = await apiClient.get<EstadoCuenta>(`/clientes/${cliente_id}/cuenta`)
  return data
}

export async function crearMovimiento(
  cliente_id: string,
  datos: MovimientoCreate,
): Promise<EstadoCuenta> {
  const { data } = await apiClient.post<EstadoCuenta>(`/clientes/${cliente_id}/movimientos`, datos)
  return data
}

export async function actualizarMovimiento(
  cliente_id: string,
  movimiento_id: string,
  datos: Partial<MovimientoCreate>,
): Promise<EstadoCuenta> {
  const { data } = await apiClient.patch<EstadoCuenta>(
    `/clientes/${cliente_id}/movimientos/${movimiento_id}`,
    datos,
  )
  return data
}

export async function eliminarMovimiento(
  cliente_id: string,
  movimiento_id: string,
): Promise<EstadoCuenta> {
  const { data } = await apiClient.delete<EstadoCuenta>(
    `/clientes/${cliente_id}/movimientos/${movimiento_id}`,
  )
  return data
}
