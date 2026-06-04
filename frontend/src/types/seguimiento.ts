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

export interface Hito {
  fecha?: string | null
  nota?: string | null
}

export interface Seguimiento {
  estado: string
  novedades?: string | null
  numero_tracking?: string | null
  naviera?: string | null
  url_tracking?: string | null
  fecha_eta?: string | null
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
  hitos?: Record<string, Hito> | null
}
