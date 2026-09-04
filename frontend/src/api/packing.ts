import apiClient from './client'
import { TIMEOUT_SUBIDA } from '../lib/imagenes'
import type { ItemCreate, ItemResponse, Sesion } from '../types/packing'

// Adjunta el token de localStorage en cada request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('yuda_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function getSesiones(): Promise<Sesion[]> {
  const { data } = await apiClient.get<Sesion[]>('/sesiones')
  return data
}

export async function crearSesion(datos: {
  nombre_cliente: string
  tipo_cambio_usd?: number
  cliente_id?: string | null
}): Promise<Sesion> {
  const { data } = await apiClient.post<Sesion>('/sesiones', datos)
  return data
}

export async function getItems(sesion_id: string): Promise<ItemResponse[]> {
  const { data } = await apiClient.get<ItemResponse[]>(`/sesiones/${sesion_id}/items`)
  return data
}

export async function crearItem(sesion_id: string, datos: ItemCreate): Promise<ItemResponse> {
  const { data } = await apiClient.post<ItemResponse>(`/sesiones/${sesion_id}/items`, datos)
  return data
}

export async function actualizarItem(
  sesion_id: string,
  item_id: string,
  datos: Partial<ItemCreate>,
): Promise<ItemResponse> {
  const { data } = await apiClient.patch<ItemResponse>(
    `/sesiones/${sesion_id}/items/${item_id}`,
    datos,
  )
  return data
}

export async function eliminarItem(sesion_id: string, item_id: string): Promise<void> {
  await apiClient.delete(`/sesiones/${sesion_id}/items/${item_id}`)
}

// Sube/reemplaza la foto FINAL (limpia) de un producto. Solo se usa en los
// documentos del cliente y del proveedor; el OCR no la toca.
// Recorta a mano la foto de un producto cuando el recorte automatico salio mal.
// `recuadro` es [x0, y0, x1, y1] en fracciones de 0 a 1; en null se vuelve a la
// foto completa. El recorte lo hace el backend, con el mismo codigo que el automatico.
export async function guardarRecorte(
  sesion_id: string,
  item_id: string,
  recuadro: number[] | null,
): Promise<ItemResponse> {
  const { data } = await apiClient.post<ItemResponse>(
    `/sesiones/${sesion_id}/items/${item_id}/recorte`,
    { recuadro },
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

export async function eliminarSesion(sesion_id: string): Promise<void> {
  await apiClient.delete(`/sesiones/${sesion_id}`)
}

export async function exportarPackingExcel(sesion_id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/sesiones/${sesion_id}/exportar/packing-excel`, {
    responseType: 'blob',
  })
  return data as Blob
}

export async function exportarPackingPDF(sesion_id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/sesiones/${sesion_id}/exportar/packing-pdf`, {
    responseType: 'blob',
  })
  return data as Blob
}

export async function exportarCotizacionExcel(sesion_id: string, idioma: string): Promise<Blob> {
  const { data } = await apiClient.post(
    `/sesiones/${sesion_id}/exportar/cotizacion-excel`,
    { idioma },
    { responseType: 'blob' },
  )
  return data as Blob
}

export async function exportarCotizacionPDF(sesion_id: string, idioma: string): Promise<Blob> {
  const { data } = await apiClient.post(
    `/sesiones/${sesion_id}/exportar/cotizacion-pdf`,
    { idioma },
    { responseType: 'blob' },
  )
  return data as Blob
}

export interface FacturaOpciones {
  contenedor_id?: string | null
  de?: string | null
  para?: string | null
}

export async function exportarFacturaPDF(sesion_id: string, opciones: FacturaOpciones = {}): Promise<Blob> {
  const { data } = await apiClient.post(
    `/sesiones/${sesion_id}/exportar/factura-pdf`,
    { contenedor_id: opciones.contenedor_id ?? null, de: opciones.de ?? null, para: opciones.para ?? null },
    { responseType: 'blob' },
  )
  return data as Blob
}

export async function exportarFacturaExcel(sesion_id: string, opciones: FacturaOpciones = {}): Promise<Blob> {
  const { data } = await apiClient.post(
    `/sesiones/${sesion_id}/exportar/factura-excel`,
    { contenedor_id: opciones.contenedor_id ?? null, de: opciones.de ?? null, para: opciones.para ?? null },
    { responseType: 'blob' },
  )
  return data as Blob
}
