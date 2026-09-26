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
  // Fecha aproximada que dio ESTE proveedor (no toda la cotización).
  fecha_tentativa_entrega?: string | null
  // Para que Marcela (super admin) vea quién hizo cada paso, no solo que
  // "ya se hizo". None en pedidos de antes de este cambio.
  generado_por_nombre?: string | null
  revisado_por_nombre?: string | null
}

export interface ActividadBodega {
  usuario_nombre: string | null
  tipo: string
  detalle: string | null
  created_at: string
}

export interface PedidoBodegaSeguimiento {
  sesion_id: string
  numero: string
  cliente_nombre: string
  fecha: string
  estado_envio: string
  total_ordenes: number
  ordenes_revisadas: number
  bodega_asignado_a_id: string | null
  bodega_asignado_a_nombre: string | null
  actividad_reciente: ActividadBodega[]
}
