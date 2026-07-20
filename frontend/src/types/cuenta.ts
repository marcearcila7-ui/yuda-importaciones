export interface Movimiento {
  id: string
  cliente_id: string
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
  movimientos: Movimiento[]
}

export interface MovimientoCreate {
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
