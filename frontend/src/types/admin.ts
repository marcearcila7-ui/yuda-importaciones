export interface UsuarioAdmin {
  id: string
  nombre: string
  email: string
  rol: 'admin' | 'vendedora' | 'contadora'
  activo: boolean
  created_at: string
}

export interface UsuarioCreate {
  nombre: string
  email: string
  password: string
  rol: 'admin' | 'vendedora' | 'contadora'
}

export interface ConfiguracionResponse {
  tipo_cambio_usd: number
  updated_at: string | null
}

export interface SesionHistorial {
  id: string
  nombre_cliente: string
  fecha: string
  total_items: number
  total_rmb: number
  total_usd: number
  cantidad_proveedores: number
  tiene_pedidos: boolean
  created_at: string
}
