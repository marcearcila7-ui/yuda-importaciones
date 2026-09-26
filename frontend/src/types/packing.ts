export interface ItemCreate {
  supplier_nombre?: string
  supplier_numero?: string
  foto_url?: string
  // Foto final (limpia) para los documentos de cliente/proveedor; si falta se usa foto_url.
  foto_final_url?: string | null
  // Marca de fabrica y fecha de entrega del proveedor: los llena la vendedora
  marca?: string | null
  fecha_recibo?: string | null
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
  // Colores/variantes: el OCR ya lo lee siempre, no solo en bolsos.
  colores?: string | null
  // Campos propios de una cotización de bolsos (sesion.tipo_cotizacion === 'bolsos').
  tamano?: string | null
  empaque?: string | null
  etiqueta?: string | null
  herrajes?: string | null
  riata?: string | null
  // Mínimo que exige la TIENDA en total: puede ser solo cajas, o cajas + piezas.
  minimo_cajas_tienda?: number | null
  minimo_piezas_caja_tienda?: number | null
  // Fotos de detalle del bolso: {"interior": url, "herrajes": url, ...}
  fotos_extra?: Record<string, string> | null
  // Recortes a mano de las de arriba, hechos ya durante la carga masiva (antes
  // de agregar el producto): sin esto se perdían al pasar de resultado de OCR
  // a ítem real de la cotización.
  fotos_extra_final?: Record<string, string> | null
  // Si viene de un resultado de carga masiva: marca ese resultado como ya
  // agregado para que no se ofrezca ni se duplique si se retoma el lote.
  lote_item_id?: string
}

export interface ItemResponse extends ItemCreate {
  id: string
  sesion_id: string
  foto_url?: string
  // Referencia de catálogo que ve el cliente (la asigna el sistema)
  referencia?: string | null
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
  // "productos" (default) o "bolsos": cambia qué datos pide el OCR.
  tipo_cotizacion: 'productos' | 'bolsos'
  tipo_cambio_usd: number
  user_id: string
  cliente_id?: string | null
  contenedor_id?: string | null
  // Marca de embarque: identifica la carga del cliente dentro del contenedor
  shipping_mark?: string | null
  enviada_cliente?: boolean
  notas_cliente?: string | null
  pedido_recibido_at?: string | null
  pedido_estado?: string | null
  pedido_confirmado_at?: string | null
  orden_compra_url?: string | null
  orden_compra_nombre?: string | null
  created_at: string
  // Etapa real del envío (ESTADOS_ENVIO backend), null si aún no tiene
  // seguimiento (todavía no llegó a "cotización enviada").
  estado_envio?: string | null
  // Con estado_envio === 'en_bodega' a secas no se distingue "bodega la está
  // revisando" de "bodega ya se la envió al cliente a aprobar": estos dos
  // campos son los que permiten esa distinción.
  cliente_aprobo_despacho_at?: string | null
  aprobacion_limite_at?: string | null
}
