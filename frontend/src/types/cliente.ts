export interface Cliente {
  id: string
  nombre: string
  email: string
  empresa: string | null
  nit: string | null
  telefono: string | null
  pais: string | null
  vendedora_id: string
  activo: boolean
  created_at: string
}

export interface ClienteCreado extends Cliente {
  password_inicial: string
}

export interface ClienteCreate {
  nombre: string
  email: string
  empresa?: string
  nit?: string
  telefono?: string
  pais?: string
  password?: string
}
