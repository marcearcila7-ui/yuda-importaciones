import apiClient from './client'
import { TIMEOUT_SUBIDA } from '../lib/imagenes'
import type { OCRResultado, TipoFotoExtra } from '../types/ocr'

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

// Sube una foto de detalle (las del bolso, o una de las 3 genéricas
// extra1/2/3 para cualquier producto), aparte de la que ya lee el OCR.
// Devuelve el ítem completo con `datos.fotos_extra` actualizado.
export async function subirFotoExtra(
  lote_id: string,
  item_id: string,
  tipo: TipoFotoExtra,
  file: File,
): Promise<{ tipo: string; foto_url: string }> {
  const fd = new FormData()
  fd.append('foto', file)
  fd.append('tipo', tipo)
  const { data } = await apiClient.post(
    `/lotes/${lote_id}/items/${item_id}/foto-extra`,
    fd,
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

// Recorta/gira a mano la foto principal de un resultado de carga masiva,
// antes de agregarlo como ítem real. `recuadro` es [x0,y0,x1,y1] en fracciones
// de 0 a 1; en null se vuelve a la foto completa (o solo se aplica el giro).
export async function recortarItemLote(
  lote_id: string,
  item_id: string,
  recuadro: number[] | null,
  giro = 0,
): Promise<LoteItemInfo> {
  const { data } = await apiClient.post<LoteItemInfo>(
    `/lotes/${lote_id}/items/${item_id}/recorte`,
    { recuadro, giro },
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

// Igual, para una foto de detalle (interior/herrajes/riata/exterior, o una
// genérica extra1/2/3). Siempre parte de la foto original de ese tipo.
export async function recortarFotoExtraLote(
  lote_id: string,
  item_id: string,
  tipo: TipoFotoExtra,
  recuadro: number[] | null,
  giro = 0,
): Promise<LoteItemInfo> {
  const { data } = await apiClient.post<LoteItemInfo>(
    `/lotes/${lote_id}/items/${item_id}/fotos-extra/${tipo}/recorte`,
    { recuadro, giro },
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
