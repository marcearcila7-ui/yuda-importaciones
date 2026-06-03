export interface ItemCreate {
  supplier_nombre?: string
  supplier_numero?: string
  foto_url?: string
  item_no?: string
  descripcion_es?: string
  descripcion_en?: string
  descripcion_zh?: string
  material?: string
  uso?: string
  qty_por_ctn: number
  price_rmb: number
  gw?: number
  largo_cm?: number
  ancho_cm?: number
  alto_cm?: number
  ctns: number
  orden?: number
}

export interface ItemResponse extends ItemCreate {
  id: string
  sesion_id: string
  foto_url?: string
  t_qty: number
  total_rmb: number
  price_usd: number
  total_usd: number
  cbm: number
  t_cbm: number
  t_gw: number
}

export interface Sesion {
  id: string
  nombre_cliente: string
  fecha: string
  tipo_cambio_usd: number
  user_id: string
  created_at: string
}
