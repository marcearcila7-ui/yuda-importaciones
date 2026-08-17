import apiClient from './client'
import { TIMEOUT_SUBIDA } from '../lib/imagenes'
import type { OCRResultado } from '../types/ocr'

export interface LoteItemInfo {
  id: string
  foto_url: string
  estado: string
  datos: OCRResultado | null
}

export interface LoteEstadoResp {
  id: string
  sesion_id: string
  estado: string
  total: number
  procesadas: number
  items: LoteItemInfo[]
}

export async function crearLote(sesion_id: string): Promise<{ lote_id: string }> {
  const { data } = await apiClient.post(`/sesiones/${sesion_id}/lotes`)
  return data
}

export async function subirFotoLote(lote_id: string, file: File): Promise<void> {
  const fd = new FormData()
  fd.append('foto', file)
  await apiClient.post(`/lotes/${lote_id}/foto`, fd, { timeout: TIMEOUT_SUBIDA })
}

export async function procesarLoteApi(lote_id: string): Promise<void> {
  await apiClient.post(`/lotes/${lote_id}/procesar`)
}

export async function reprocesarLote(lote_id: string): Promise<void> {
  await apiClient.post(`/lotes/${lote_id}/reprocesar`)
}

// Reintento con IA sobre la MISMA foto de un ítem puntual.
export async function reanalizarItemLote(lote_id: string, item_id: string): Promise<LoteItemInfo> {
  const { data } = await apiClient.post<LoteItemInfo>(`/lotes/${lote_id}/items/${item_id}/reanalizar`)
  return data
}

// Reemplaza la foto de un ítem por otra y la reanaliza al instante.
export async function reemplazarItemLote(
  lote_id: string,
  item_id: string,
  file: File,
): Promise<LoteItemInfo> {
  const fd = new FormData()
  fd.append('foto', file)
  const { data } = await apiClient.post<LoteItemInfo>(
    `/lotes/${lote_id}/items/${item_id}/reemplazar`,
    fd,
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

export async function estadoLote(lote_id: string): Promise<LoteEstadoResp> {
  const { data } = await apiClient.get(`/lotes/${lote_id}`)
  return data as LoteEstadoResp
}

export async function loteActivo(sesion_id: string): Promise<{ lote_id: string | null; estado?: string }> {
  const { data } = await apiClient.get(`/sesiones/${sesion_id}/lotes/activo`)
  return data
}

export async function borrarLote(lote_id: string): Promise<void> {
  await apiClient.delete(`/lotes/${lote_id}`)
}
