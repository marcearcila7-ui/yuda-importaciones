import type { Seguimiento } from './seguimiento'

export interface ClientePortal {
  id: string
  nombre: string
  email: string
  empresa: string | null
  pais: string | null
}

export interface PortalTokenResponse {
  access_token: string
  token_type: string
  cliente: ClientePortal
}

export interface CotizacionResumen {
  sesion_id: string
  numero: string
  nombre_cliente: string
  fecha: string
  total_items: number
  total_usd: number
  estado: string
  actualizado: string | null
}

export interface PortalItem {
  foto_url: string | null
  descripcion_es: string | null
  descripcion_en: string | null
  descripcion_zh: string | null
  ctns: number
  qty_por_ctn: number
  t_qty: number
  price_usd: number
  total_usd: number
  cbm: number
  t_cbm: number
}

export interface CotizacionDetalle {
  sesion_id: string
  numero: string
  nombre_cliente: string
  fecha: string
  items: PortalItem[]
  total_usd: number
  total_cbm: number
  seguimiento: Seguimiento
}
