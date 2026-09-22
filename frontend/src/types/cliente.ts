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
  // "manual" (se creó a mano, el caso normal) o "importado_contable" (entró
  // en bloque al importar el listado de Yuda Contable).
  origen: 'manual' | 'importado_contable'
  // true si es un importado que todavía nadie asignó a una vendedora real
  // (sigue a nombre del admin que lo importó) -se muestra aparte de los
  // clientes reales, no mezclado en la misma lista.
  pendiente_asignacion: boolean
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

// ──────────────── Importar clientes de Yuda Contable ────────────────

export interface ContableClientePreview {
  sigla: string
  nombre: string | null
  pais: string | null
  telefono: string | null
  ya_existe: boolean
  cliente_id_existente: string | null
}

export interface ImportarContableResultado {
  creados: number
  omitidos: number
}
