export interface Cliente {
  id: string
  nombre: string
  email: string
  empresa: string | null
  nit: string | null
  telefono: string | null
  pais: string | null
  vendedora_id: string
  // Código con el que este cliente aparece en Yuda Contable (app aparte).
  // Solo una etiqueta de referencia; nunca trae saldos ni movimientos.
  sigla: string | null
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

// ──────────────── Colaboración: clientes compartidos entre vendedoras ────────────────

export interface VendedoraBasica {
  id: string
  nombre: string
  email: string
}

export interface VendedoraAsignada {
  vendedora: VendedoraBasica
  asignado_por: string | null
  created_at: string
}

export interface ActividadCliente {
  id: string
  usuario_id: string
  usuario_nombre: string
  nota: string
  created_at: string
}

export interface CotizacionResumenCliente {
  sesion_id: string
  numero: string
  fecha: string
  vendedora_nombre: string
  pedido_estado: string | null
  estado_envio: string | null
}

export interface ClienteColaboracion {
  duena: VendedoraBasica
  asignadas: VendedoraAsignada[]
  cotizaciones: CotizacionResumenCliente[]
  actividad: ActividadCliente[]
}
