import apiClient from './client'
import type {
  ActividadCliente,
  Cliente,
  ClienteColaboracion,
  ContableClientePreview,
  ImportarContableResultado,
  VendedoraAsignada,
} from '../types/cliente'
import type { Sesion } from '../types/packing'
import type { Adjunto, Seguimiento, SeguimientoUpdate } from '../types/seguimiento'

// El interceptor de token (yuda_token) ya está registrado en api/admin.ts

export async function getClientes(): Promise<Cliente[]> {
  const { data } = await apiClient.get<Cliente[]>('/clientes')
  return data
}

export async function getCliente(id: string): Promise<Cliente> {
  const { data } = await apiClient.get<Cliente>(`/clientes/${id}`)
  return data
}

export async function actualizarCliente(
  id: string,
  datos: Partial<{
    nombre: string
    empresa: string
    telefono: string
    pais: string
    activo: boolean
    // Reasignar la vendedora dueña: exclusivo de admin (lo valida el backend).
    vendedora_id: string
    // Código de Yuda Contable: exclusivo de admin (lo valida el backend).
    sigla: string
  }>,
): Promise<Cliente> {
  const { data } = await apiClient.patch<Cliente>(`/clientes/${id}`, datos)
  return data
}

export async function resetPasswordCliente(id: string, nueva_password: string): Promise<void> {
  await apiClient.post(`/clientes/${id}/reset-password`, { nueva_password })
}

// Estado de cuenta oficial de Yuda Contable (PDF/imagen que Marcela sube a
// mano): sin conexión en vivo entre las dos apps, esto solo guarda un
// documento puntual y lo muestra en el portal del cliente.
export async function subirEstadoCuentaOficial(id: string, archivo: File): Promise<Cliente> {
  const form = new FormData()
  form.append('archivo', archivo)
  const { data } = await apiClient.post<Cliente>(
    `/clientes/${id}/estado-cuenta-oficial`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export async function quitarEstadoCuentaOficial(id: string): Promise<Cliente> {
  const { data } = await apiClient.delete<Cliente>(`/clientes/${id}/estado-cuenta-oficial`)
  return data
}

export async function eliminarCliente(id: string): Promise<void> {
  await apiClient.delete(`/clientes/${id}`)
}

export async function getCotizacionesCliente(id: string): Promise<Sesion[]> {
  const { data } = await apiClient.get<Sesion[]>(`/clientes/${id}/cotizaciones`)
  return data
}

// Vista consolidada: dueña + vendedoras compartidas, todas las cotizaciones del
// cliente (de cualquier vendedora) y la bitácora de actividad.
export async function getColaboracionCliente(id: string): Promise<ClienteColaboracion> {
  const { data } = await apiClient.get<ClienteColaboracion>(`/clientes/${id}/colaboracion`)
  return data
}

export async function agregarActividadCliente(id: string, nota: string): Promise<ActividadCliente> {
  const { data } = await apiClient.post<ActividadCliente>(`/clientes/${id}/actividad`, { nota })
  return data
}

// Marcela comparte el cliente con vendedoras adicionales (además de la dueña).
export async function asignarVendedorasCliente(
  id: string,
  vendedora_ids: string[],
): Promise<VendedoraAsignada[]> {
  const { data } = await apiClient.post<VendedoraAsignada[]>(`/clientes/${id}/vendedoras`, {
    vendedora_ids,
  })
  return data
}

export async function quitarVendedoraCliente(id: string, vendedoraId: string): Promise<void> {
  await apiClient.delete(`/clientes/${id}/vendedoras/${vendedoraId}`)
}

export async function previewImportarContable(): Promise<ContableClientePreview[]> {
  const { data } = await apiClient.get<ContableClientePreview[]>('/clientes/importar-contable/preview')
  return data
}

export async function importarContable(siglas: string[]): Promise<ImportarContableResultado> {
  const { data } = await apiClient.post<ImportarContableResultado>('/clientes/importar-contable', {
    siglas,
  })
  return data
}

// Búsqueda EN VIVO contra la API interna de Yuda Contable (no la lista fija
// de arriba). Puede tirar 502 si esa app no responde.
export async function buscarContable(q: string): Promise<ContableClientePreview[]> {
  const { data } = await apiClient.get<ContableClientePreview[]>('/clientes/buscar-contable', {
    params: { q },
  })
  return data
}

export async function importarContableUno(sigla: string): Promise<Cliente> {
  const { data } = await apiClient.post<Cliente>('/clientes/importar-contable-uno', { sigla })
  return data
}

// Todos los clientes que existen en Yuda Contable pero todavía NO en el
// cotizador (ni importados, ni sincronizados solos al crearlos allá).
export async function getClientesNoSincronizados(): Promise<ContableClientePreview[]> {
  const { data } = await apiClient.get<ContableClientePreview[]>('/clientes/no-sincronizados')
  return data
}

// El PDF oficial de Yuda Contable en vivo (no el que se sube a mano).
export async function descargarEstadoCuentaContablePdf(clienteId: string): Promise<Blob> {
  const { data } = await apiClient.get(`/clientes/${clienteId}/estado-cuenta-contable/pdf`, {
    responseType: 'blob',
  })
  return data
}

// Limpieza masiva: desactiva todos los clientes cuya vendedora dueña no esté
// en la lista dada. No borra nada, solo los saca de la UI (activo=false).
export async function desactivarClientesExcepto(vendedora_ids: string[]): Promise<{ desactivados: number }> {
  const { data } = await apiClient.post<{ desactivados: number }>('/clientes/desactivar-excepto', {
    vendedora_ids,
  })
  return data
}

export async function vincularCliente(
  sesion_id: string,
  cliente_id: string | null,
): Promise<Sesion> {
  const { data } = await apiClient.patch<Sesion>(`/sesiones/${sesion_id}/cliente`, { cliente_id })
  return data
}

export async function enviarACliente(sesion_id: string): Promise<Seguimiento> {
  const { data } = await apiClient.post<Seguimiento>(`/sesiones/${sesion_id}/enviar-cliente`)
  return data
}

export async function getSeguimiento(sesion_id: string): Promise<Seguimiento | null> {
  try {
    const { data } = await apiClient.get<Seguimiento>(`/sesiones/${sesion_id}/seguimiento`)
    return data
  } catch {
    // 404: la cotización aún no se envió al cliente
    return null
  }
}

export async function guardarSeguimiento(
  sesion_id: string,
  datos: SeguimientoUpdate,
): Promise<Seguimiento> {
  const { data } = await apiClient.put<Seguimiento>(`/sesiones/${sesion_id}/seguimiento`, datos)
  return data
}

// La vendedora ajusta las cantidades del cliente y le devuelve la cotización a
// confirmar (estado "por confirmar"). Devuelve la sesión actualizada.
export async function enviarAConfirmar(
  sesion_id: string,
  items: Array<{ item_id: string; cantidad: number }>,
): Promise<Sesion> {
  const { data } = await apiClient.put<Sesion>(`/sesiones/${sesion_id}/enviar-a-confirmar`, { items })
  return data
}

// Sube el PDF del BL (solo admin) y devuelve su URL pública
export async function subirBlPdf(sesion_id: string, archivo: File): Promise<string> {
  const form = new FormData()
  form.append('archivo', archivo)
  const { data } = await apiClient.post<{ url: string }>(
    `/sesiones/${sesion_id}/seguimiento/bl-pdf`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data.url
}

// Sube un adjunto (PDF o imagen) de una etapa; el cliente lo verá en el tracking
export async function subirAdjuntoSeguimiento(
  sesion_id: string,
  archivo: File,
): Promise<Adjunto> {
  const form = new FormData()
  form.append('archivo', archivo)
  const { data } = await apiClient.post<Adjunto>(
    `/sesiones/${sesion_id}/seguimiento/adjunto`,
    form,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

