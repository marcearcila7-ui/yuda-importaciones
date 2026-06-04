export interface EquipoCotizacion {
  sesion_id: string
  numero: string
  fecha: string
  nombre_cliente: string
  enviada: boolean
  estado: string | null
}

export interface EquipoCliente {
  id: string
  nombre: string
  email: string
  empresa: string | null
  pais: string | null
  activo: boolean
  cotizaciones: EquipoCotizacion[]
}

export interface EquipoVendedora {
  user_id: string
  nombre: string
  email: string
  total_clientes: number
  clientes: EquipoCliente[]
}

export interface EquipoResponse {
  vendedoras: EquipoVendedora[]
}
