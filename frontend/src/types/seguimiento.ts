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
  tipo?: string | null // 'pdf' | 'imagen'
}

export interface Hito {
  fecha?: string | null
  nota?: string | null
  adjuntos?: Adjunto[] | null
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
  hitos?: Record<string, Hito> | null
}
