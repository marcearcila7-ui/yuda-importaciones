export type EstadoContenedor = 'abierto' | 'en_transito' | 'cerrado'

export interface Contenedor {
  id: string
  codigo: string
  trm_usd: number
  fecha?: string | null
  estado: EstadoContenedor
  notas?: string | null
  created_at: string
}

export interface ContenedorCreate {
  codigo: string
  trm_usd: number
  fecha?: string | null
  estado?: EstadoContenedor
  notas?: string | null
}
