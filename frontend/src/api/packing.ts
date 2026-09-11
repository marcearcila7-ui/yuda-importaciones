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
  tipo_cotizacion?: 'productos' | 'bolsos'
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
// Marca de embarque de la cotizacion: la misma para todos sus productos, por eso
// se guarda en la cotizacion y no en cada uno.
export async function guardarShippingMark(sesion_id: string, shipping_mark: string) {
  const { data } = await apiClient.patch(`/sesiones/${sesion_id}`, { shipping_mark })
  return data
}

// Recorta a mano la foto de un producto cuando el recorte automatico salio mal.
// `recuadro` es [x0, y0, x1, y1] en fracciones de 0 a 1; en null se vuelve a la
// foto completa. El recorte lo hace el backend, con el mismo codigo que el automatico.
export async function guardarRecorte(
  sesion_id: string,
  item_id: string,
  recuadro: number[] | null,
  giro = 0,
): Promise<ItemResponse> {
  const { data } = await apiClient.post<ItemResponse>(
    `/sesiones/${sesion_id}/items/${item_id}/recorte`,
    { recuadro, giro },
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

// Recorta/gira a mano una foto de detalle del bolso (interior/herrajes/riata/
// exterior). Igual que guardarRecorte, pero siempre parte de la foto ORIGINAL
// subida para ese tipo (fotos_extra), nunca de un recorte previo.
export async function guardarRecorteFotoExtra(
  sesion_id: string,
  item_id: string,
  tipo: string,
  recuadro: number[] | null,
  giro = 0,
): Promise<ItemResponse> {
  const { data } = await apiClient.post<ItemResponse>(
    `/sesiones/${sesion_id}/items/${item_id}/fotos-extra/${tipo}/recorte`,
    { recuadro, giro },
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

// Reemplaza la foto de un producto ya agregado a la cotización por una
// completamente distinta (no un recorte de la misma). Descarta cualquier
// recorte anterior en el backend: no tiene sentido sobre una foto distinta.
export async function reemplazarFotoItem(
  sesion_id: string,
  item_id: string,
  file: File,
): Promise<ItemResponse> {
  const fd = new FormData()
  fd.append('foto', file)
  const { data } = await apiClient.post<ItemResponse>(
    `/sesiones/${sesion_id}/items/${item_id}/foto`,
    fd,
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

// Igual, para una foto de detalle del bolso (interior/herrajes/riata/exterior).
export async function reemplazarFotoExtra(
  sesion_id: string,
  item_id: string,
  tipo: string,
  file: File,
): Promise<ItemResponse> {
  const fd = new FormData()
  fd.append('foto', file)
  const { data } = await apiClient.post<ItemResponse>(
    `/sesiones/${sesion_id}/items/${item_id}/fotos-extra/${tipo}/foto`,
    fd,
    { timeout: TIMEOUT_SUBIDA },
  )
  return data
}

export async function eliminarSesion(sesion_id: string): Promise<void> {
  await apiClient.delete(`/sesiones/${sesion_id}`)
}

// Estos 4 generan un PDF/Excel con fotos incrustadas: pueden tardar más que el
// timeout por default de apiClient, así que usan el mismo margen que las subidas.
export async function exportarPackingExcel(sesion_id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/sesiones/${sesion_id}/exportar/packing-excel`, {
    responseType: 'blob',
    timeout: TIMEOUT_SUBIDA,
  })
  return data as Blob
}

export async function exportarPackingPDF(sesion_id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/sesiones/${sesion_id}/exportar/packing-pdf`, {
    responseType: 'blob',
    timeout: TIMEOUT_SUBIDA,
  })
  return data as Blob
}

// `columnas`: claves de columna a mostrar (ver CLAVES_COLUMNAS en el backend);
// sin pasarlo (o null) salen todas, igual que siempre.
export async function exportarCotizacionExcel(
  sesion_id: string,
  idioma: string,
  columnas?: string[] | null,
): Promise<Blob> {
  const { data } = await apiClient.post(
    `/sesiones/${sesion_id}/exportar/cotizacion-excel`,
    { idioma, columnas },
    { responseType: 'blob', timeout: TIMEOUT_SUBIDA },
  )
  return data as Blob
}

export async function exportarCotizacionPDF(
  sesion_id: string,
  idioma: string,
  columnas?: string[] | null,
): Promise<Blob> {
  const { data } = await apiClient.post(
    `/sesiones/${sesion_id}/exportar/cotizacion-pdf`,
    { idioma, columnas },
    { responseType: 'blob', timeout: TIMEOUT_SUBIDA },
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
