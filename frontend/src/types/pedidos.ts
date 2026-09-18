export interface PedidoGeneradoInfo {
  supplier: string
  archivo_nombre: string
  url_descarga: string
  url_pdf?: string | null
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
  archivo_pdf_url?: string | null
  archivo_csv_url?: string | null
  archivo_real_xlsx_url?: string | null
  archivo_real_pdf_url?: string | null
  archivo_real_csv_url?: string | null
  revisado_en_bodega_at?: string | null
  fecha_generacion: string
}
