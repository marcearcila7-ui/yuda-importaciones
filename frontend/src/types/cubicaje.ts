export interface CubicajeResumen {
  cbm_calculado: number
  limite_min: number
  limite_max: number
  resultado: 'sobra' | 'falta' | 'ajustado'
  referencias: string[]
}

export interface CubicajeAdjunto {
  url: string
  nombre?: string | null
  tipo?: 'imagen' | 'video' | 'pdf' | 'excel' | 'csv' | null
}

export interface CubicajeMensaje {
  id: string
  tipo: 'reporte' | 'nota' | 'respuesta'
  autor_id: string
  autor_nombre: string | null
  mensaje: string | null
  cbm_calculado: number | null
  cbm_ajustado: number | null
  resultado: string | null
  referencia: string | null
  cajas_afectadas: number | null
  espacio_restante_cbm: number | null
  adjuntos: CubicajeAdjunto[] | null
  created_at: string
}

export interface CubicajeDetalle {
  resumen: CubicajeResumen
  mensajes: CubicajeMensaje[]
  // Con quién es la conversación, del lado del cotizador: la persona de
  // bodega que tiene asignado el pedido (null si nadie lo ha tomado).
  vendedora_nombre: string | null
  bodega_asignado_a_nombre: string | null
}
