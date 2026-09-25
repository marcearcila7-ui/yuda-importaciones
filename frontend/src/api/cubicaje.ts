import apiClient from './client'
import type { CubicajeAdjunto, CubicajeDetalle } from '../types/cubicaje'

// El cálculo en vivo del cubicaje del pedido + el hilo completo de reportes,
// notas y respuestas. Se llama con polling rápido para que llegue casi al
// instante sin recargar la página.
export async function getCubicaje(sesionId: string): Promise<CubicajeDetalle> {
  const { data } = await apiClient.get<CubicajeDetalle>(`/sesiones/${sesionId}/cubicaje`)
  return data
}

// La vendedora (o Marcela) responde en el hilo de cubicaje de este pedido,
// con foto(s)/video(s)/archivo(s) opcionales (ya subidos con subirAdjuntoCubicaje).
export async function responderCubicaje(
  sesionId: string,
  mensaje: string,
  adjuntos?: CubicajeAdjunto[],
): Promise<void> {
  await apiClient.post(`/sesiones/${sesionId}/cubicaje/responder`, { mensaje, adjuntos })
}

// Sube una foto, video o archivo para adjuntarlo a un mensaje del hilo de
// cubicaje. Devuelve {url, nombre, tipo}: el mensaje se manda aparte, con
// esto ya incluido en su lista de adjuntos.
export async function subirAdjuntoCubicaje(sesionId: string, archivo: File): Promise<CubicajeAdjunto> {
  const form = new FormData()
  form.append('archivo', archivo)
  const { data } = await apiClient.post<CubicajeAdjunto>(
    `/sesiones/${sesionId}/cubicaje/adjunto`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}
