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

// Login con el enlace mágico de un aviso automático (ej. "tu pedido está
// listo para aprobar"): igual que un login normal, más a qué cotización
// llevar al cliente.
export interface MagicLoginResponse extends PortalTokenResponse {
  sesion_id: string
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

export interface PortalInspeccionItem {
  fotos: string[]
  video_url: string | null
  referencia_coincide: boolean | null
  descripcion_es: string | null
  descripcion_en: string | null
  ctns: number | null
  qty_por_ctn: number | null
}

export interface PortalItem {
  item_id: string
  foto_url: string | null
  referencia: string | null
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
  cantidad_solicitada: number | null
  inspeccion_bodega: PortalInspeccionItem | null
}

export interface PortalPedidoGeneradoResumen {
  supplier: string
  fecha_tentativa_entrega: string | null
  revisado_en_bodega_at: string | null
  archivo_real_xlsx_url: string | null
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
  notas_cliente: string | null
  pedido_recibido: boolean
  pedido_estado: string | null
  pedido_confirmado: boolean
  orden_compra_url: string | null
  orden_compra_nombre: string | null
  pedidos_generados: PortalPedidoGeneradoResumen[]
}

export interface PortalPedidoInput {
  items: { item_id: string; cantidad: number }[]
  notas: string | null
}
