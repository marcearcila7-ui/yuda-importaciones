// Hitos del envío en orden (deben coincidir con ESTADOS_ENVIO del backend)
export const ESTADOS_ENVIO = [
  'cotizacion_enviada',
  'pedido_confirmado',
  'proveedor_recibio',
  'en_bodega',
  'en_transito',
  'en_destino',
  'entregado',
] as const

export type EstadoEnvio = (typeof ESTADOS_ENVIO)[number]

// Top 20 navieras internacionales que Marcela puede seleccionar al cargar el BL.
// Si la naviera no está en la lista, escribe el nombre en el campo "Otra".
export const NAVIERAS = [
  'MSC (Mediterranean Shipping Company)',
  'Maersk',
  'CMA CGM',
  'COSCO Shipping Lines',
  'Hapag-Lloyd',
  'ONE (Ocean Network Express)',
  'Evergreen Marine',
  'HMM (Hyundai Merchant Marine)',
  'Yang Ming Marine Transport',
  'ZIM Integrated Shipping Services',
  'PIL (Pacific International Lines)',
  'Wan Hai Lines',
  'SITC Container Lines',
  'TS Lines',
  'OOCL',
  'Matson',
  'SeaLead Shipping',
  'Emirates Shipping Line',
  'KMTC Line',
  'Sinokor Merchant Marine',
] as const

// Etapas que la vendedora puede gestionar. De "en_transito" en adelante la
// información del envío (naviera, tracking, BL) es exclusiva de Marcela.
export const ESTADOS_VENDEDORA = [
  'cotizacion_enviada',
  'pedido_confirmado',
  'proveedor_recibio',
  'en_bodega',
] as const

export interface Adjunto {
  url: string
  nombre?: string | null
  tipo?: string | null // 'pdf' | 'imagen' | 'csv' | 'excel'
}

// Lo que acepta el input de archivo del adjunto. Se listan las extensiones además
// de los MIME porque el navegador manda un content-type poco fiable para CSV/Excel.
export const ADJUNTO_ACCEPT =
  '.pdf,.jpg,.jpeg,.png,.webp,.csv,.xls,.xlsx,' +
  'application/pdf,image/jpeg,image/png,image/webp,text/csv,' +
  'application/vnd.ms-excel,' +
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

export interface Hito {
  fecha?: string | null
  nota?: string | null
  adjuntos?: Adjunto[] | null
  // Sello automático de fecha+hora (ISO) del momento en que se alcanzó la etapa.
  // Lo pone el servidor y se conserva; el editor lo muestra pero no lo edita.
  ts?: string | null
}

export interface Seguimiento {
  estado: string
  novedades?: string | null
  numero_tracking?: string | null
  naviera?: string | null
  url_tracking?: string | null
  fecha_eta?: string | null
  bl_numero?: string | null
  bl_pdf_url?: string | null
  monto_venta?: number | null
  despachado_at?: string | null
  hitos?: Record<string, Hito> | null
  updated_at?: string | null
}

export interface SeguimientoUpdate {
  estado: string
  novedades?: string | null
  numero_tracking?: string | null
  naviera?: string | null
  url_tracking?: string | null
  fecha_eta?: string | null
  bl_numero?: string | null
  bl_pdf_url?: string | null
  monto_venta?: number | null
  hitos?: Record<string, Hito> | null
}
