// Panel de ventas de Marcela (endpoint /admin/ventas)

export interface DespachoVenta {
  sesion_id: string
  numero: string
  cliente: string
  vendedora: string
  es_vendedora: boolean
  estado: string
  bl_numero: string | null
  naviera: string | null
  monto_venta: number
  despachado_at: string | null
  fecha_cotizacion: string
}

export interface VendedoraVenta {
  vendedora_id: string
  nombre: string
  cotizaciones: number
  contenedores: number
  ventas: number
}

export interface PanelVentas {
  desde: string | null
  hasta: string | null
  ventas_total: number
  pedidos_en_transito: number
  cotizaciones_hechas: number
  contenedores_total: number
  contenedores_vendedoras: number
  ventas_vendedoras: number
  por_vendedora: VendedoraVenta[]
  despachos: DespachoVenta[]
}
