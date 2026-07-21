export interface Movimiento {
  id: string
  cliente_id: string
  sesion_id: string | null
  contenedor_id: string | null
  envio: string | null
  fecha: string | null
  guia: string | null
  descripcion: string | null
  valor_mercancia: number
  comision_yuda: number
  abono: number
  saldo: number
  nota: string | null
  created_at: string
}

// Apartado de la cuenta correspondiente a un pedido (cotización), con su saldo propio.
export interface PedidoCuenta {
  sesion_id: string | null
  pedido_numero: string | null
  pedido_fecha: string | null
  es_pedido: boolean
  compras_totales: number
  comision_total: number
  abonos_totales: number
  saldo_pendiente: number
  movimientos: Movimiento[]
}

export interface EstadoCuenta {
  cliente_id: string
  nombre: string
  nit: string | null
  empresa: string | null
  compras_totales: number
  comision_total: number
  abonos_totales: number
  saldo_pendiente: number
  fecha_ultimo_abono: string | null
  pedidos: PedidoCuenta[]
}

export interface MovimientoCreate {
  sesion_id?: string | null
  contenedor_id?: string | null
  envio?: string | null
  fecha?: string | null
  guia?: string | null
  descripcion?: string | null
  valor_mercancia: number
  comision_yuda?: number | null
  abono: number
  nota?: string | null
}
