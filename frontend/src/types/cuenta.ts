export type Moneda = 'USD' | 'COP' | 'RMB' | 'EUR'
export const MONEDAS: Moneda[] = ['USD', 'COP', 'RMB', 'EUR']

// En las que el cliente puede abonar. USDT va aparte del dolar bancario porque
// se recibe y se anota distinto.
export const MONEDAS_ORIGEN = ['USDT', 'USD', 'COP', 'RMB', 'EUR'] as const

export interface Movimiento {
  id: string
  cliente_id: string
  sesion_id: string | null
  contenedor_id: string | null
  moneda: string
  envio: string | null
  fecha: string | null
  guia: string | null
  descripcion: string | null
  valor_mercancia: number
  comision_yuda: number
  abono: number
  // Como entro el abono cuando se pago en otra moneda
  monto_origen?: number | null
  moneda_origen?: string | null
  tasa_cambio?: number | null
  saldo: number
  nota: string | null
  created_at: string
}

// Apartado de la cuenta correspondiente a un pedido (cotización), con su saldo y moneda propios.
export interface PedidoCuenta {
  sesion_id: string | null
  pedido_numero: string | null
  pedido_fecha: string | null
  es_pedido: boolean
  moneda: string
  compras_totales: number
  comision_total: number
  abonos_totales: number
  saldo_pendiente: number
  movimientos: Movimiento[]
}

export interface TotalMoneda {
  moneda: string
  compras_totales: number
  comision_total: number
  abonos_totales: number
  saldo_pendiente: number
}

export interface PedidoContable {
  numero_pedido: string
  fecha_pedido: string | null
  total: number
  pendiente: number
  estado: string
  dias: number
}

export interface AbonoContable {
  fecha_abono: string | null
  monto: number
  numero_pedido: string | null
  estado: string
  es_saldo_a_favor: boolean
}

export interface EstadoCuentaContable {
  sigla: string
  moneda: string
  saldo_pendiente: number
  es_a_favor: boolean
  otros_conceptos_pendientes: number
  saldo_a_favor: number
  dias_vencido: number | null
  estado_atraso: string | null
  pedidos: PedidoContable[]
  abonos_recientes: AbonoContable[]
}

export interface EstadoCuenta {
  cliente_id: string
  nombre: string
  nit: string | null
  empresa: string | null
  totales_por_moneda: TotalMoneda[]
  fecha_ultimo_abono: string | null
  pedidos: PedidoCuenta[]
  // Documento real de Yuda Contable que Marcela subió a mano; null si nunca
  // se subió ninguno. No tiene relación con los totales de arriba. Se usa
  // solo de respaldo para clientes sin sigla (sin conexión en vivo posible).
  estado_cuenta_oficial_url: string | null
  estado_cuenta_oficial_actualizado_en: string | null
  // Estado de cuenta REAL de Yuda Contable, traído en vivo. null si el
  // cliente no tiene sigla, o si esa app no respondió.
  estado_cuenta_contable: EstadoCuentaContable | null
}

export interface MovimientoCreate {
  sesion_id?: string | null
  contenedor_id?: string | null
  moneda?: string
  envio?: string | null
  fecha?: string | null
  guia?: string | null
  descripcion?: string | null
  valor_mercancia: number
  comision_yuda?: number | null
  abono: number
  // Con monto y tasa el backend calcula el abono; asi queda el rastro de cuanto
  // entro de verdad y a que cambio, que es lo que se revisa cuando no cuadra.
  monto_origen?: number | null
  moneda_origen?: string | null
  tasa_cambio?: number | null
  nota?: string | null
}
