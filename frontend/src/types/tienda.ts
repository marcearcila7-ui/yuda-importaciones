export type EstadoPedidoTienda = 'pendiente' | 'parcial' | 'pagado'

export interface PedidoTienda {
  id: string
  nombre_tienda: string
  fecha_pedido: string | null
  monto_total: number
  monto_30: number
  monto_70: number
  monto_comision: number
  fecha_pago_30: string | null
  fecha_estimada_entrega: string | null
  fecha_real_entrega: string | null
  fecha_estimada_pago_70: string | null
  fecha_pago_70: string | null
  pct_comision_tienda: number
  fecha_comision: string | null
  empleada_id: string | null
  empleada_nombre: string | null
  notas: string | null
  estado: EstadoPedidoTienda
  dias_para_pago_70: number | null
  alerta_pago_70: boolean
  created_at: string
}

export interface PedidoTiendaCreate {
  nombre_tienda: string
  fecha_pedido?: string | null
  monto_total: number
  fecha_pago_30?: string | null
  fecha_estimada_entrega?: string | null
  fecha_real_entrega?: string | null
  fecha_estimada_pago_70?: string | null
  fecha_pago_70?: string | null
  pct_comision_tienda?: number
  fecha_comision?: string | null
  empleada_id?: string | null
  notas?: string | null
}

export interface EmpleadaResumen {
  id: string
  nombre: string
}

export interface ComisionItem {
  pedido_id: string
  nombre_tienda: string
  pct_comision_tienda: number
  monto_comision: number
  fecha_comision: string | null
  fecha_pedido: string | null
  empleada_nombre: string | null
}

export interface ComisionesReporte {
  items: ComisionItem[]
  total_comision: number
  desde: string | null
  hasta: string | null
}
