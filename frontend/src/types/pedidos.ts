export interface PedidoGeneradoInfo {
  supplier: string
  archivo_nombre: string
  url_descarga: string
  items_count: number
}

export interface GenerarPedidosResponse {
  pedidos: PedidoGeneradoInfo[]
  warnings: string[]
}

export interface PedidoGenerado {
  id: string
  sesion_id: string
  supplier: string
  archivo_xlsx_url: string
  fecha_generacion: string
}
