import apiClient from './client'
import type { CubicajeDetalle } from '../types/cubicaje'

// El cálculo en vivo del cubicaje del pedido + el hilo completo de reportes,
// notas y respuestas. Se llama con polling rápido para que llegue casi al
// instante sin recargar la página.
export async function getCubicaje(sesionId: string): Promise<CubicajeDetalle> {
  const { data } = await apiClient.get<CubicajeDetalle>(`/sesiones/${sesionId}/cubicaje`)
  return data
}

// La vendedora (o Marcela) responde en el hilo de cubicaje de este pedido.
export async function responderCubicaje(sesionId: string, mensaje: string): Promise<void> {
  await apiClient.post(`/sesiones/${sesionId}/cubicaje/responder`, { mensaje })
}
