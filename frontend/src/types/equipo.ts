export interface EquipoCotizacion {
  sesion_id: string
  numero: string
  fecha: string
  nombre_cliente: string
  enviada: boolean
  estado: string | null
  naviera: string | null
  numero_tracking: string | null
  bl_numero: string | null
  bl_pdf_url: string | null
  pendiente_bl: boolean
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
