export interface UsuarioAdmin {
  id: string
  nombre: string
  email: string
  rol: 'admin' | 'vendedora' | 'contadora' | 'bodega'
  activo: boolean
  created_at: string
}

export interface UsuarioCreate {
  nombre: string
  email: string
  password: string
  rol: 'admin' | 'vendedora' | 'contadora' | 'bodega'
}

export interface ConfiguracionResponse {
  tipo_cambio_usd: number
  updated_at: string | null
}

export interface SesionHistorial {
  id: string
  nombre_cliente: string
  vendedora_nombre: string | null
  fecha: string
  total_items: number
  total_rmb: number
  total_usd: number
  cantidad_proveedores: number
  tiene_pedidos: boolean
  created_at: string
}

export interface MetricasDashboard {
  total_sesiones_mes: number
  total_rmb_mes: number
  total_usd_mes: number
  // Valor de lo REALMENTE pedido al proveedor (cantidades de la orden ya
  // generada), no de lo cotizado: no todo lo que se cotiza se termina
  // comprando, el cliente puede quitar productos desde su portal.
  total_rmb_ordenes_mes: number
  total_usd_ordenes_mes: number
  total_items_mes: number
  total_pedidos_mes: number
  proveedores_unicos_mes: number
  pedidos_esperando_bodega: number
  pedidos_esperando_aprobacion_cliente: number
}

export interface MetricaVendedora {
  user_id: string
  nombre: string
  total_sesiones: number
  total_items: number
  total_rmb: number
  total_usd: number
  total_rmb_ordenes: number
  total_usd_ordenes: number
}

export interface MetricasVendedorasResponse {
  vendedoras: MetricaVendedora[]
}
