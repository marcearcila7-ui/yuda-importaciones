export interface CubicajeResumen {
  cbm_calculado: number
  limite_min: number
  limite_max: number
  resultado: 'sobra' | 'falta' | 'ajustado'
  referencias: string[]
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
  created_at: string
}

export interface CubicajeDetalle {
  resumen: CubicajeResumen
  mensajes: CubicajeMensaje[]
}
