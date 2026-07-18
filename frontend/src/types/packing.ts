export interface ItemCreate {
  supplier_nombre?: string
  supplier_numero?: string
  foto_url?: string
  // Foto final (limpia) para los documentos de cliente/proveedor; si falta se usa foto_url.
  foto_final_url?: string | null
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
  // CBM directo de etiqueta (opcional); si no, se calcula por dimensiones.
  cbm?: number | null
  // MQT: mínima cantidad de cajas que pide el proveedor.
  moq_cajas?: number | null
  ctns: number
  orden?: number
}

export interface ItemResponse extends ItemCreate {
  id: string
  sesion_id: string
  foto_url?: string
  cantidad_solicitada?: number | null
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
  cliente_id?: string | null
  enviada_cliente?: boolean
  notas_cliente?: string | null
  pedido_recibido_at?: string | null
  pedido_estado?: string | null
  pedido_confirmado_at?: string | null
  created_at: string
}
