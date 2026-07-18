import apiClient from './client'
import type { Cliente, ClienteCreado, ClienteCreate } from '../types/cliente'
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

export async function crearCliente(datos: ClienteCreate): Promise<ClienteCreado> {
  const { data } = await apiClient.post<ClienteCreado>('/clientes', datos)
  return data
}

export async function actualizarCliente(
  id: string,
  datos: Partial<{ nombre: string; empresa: string; telefono: string; pais: string; activo: boolean }>,
): Promise<Cliente> {
  const { data } = await apiClient.patch<Cliente>(`/clientes/${id}`, datos)
  return data
}

export async function resetPasswordCliente(id: string, nueva_password: string): Promise<void> {
  await apiClient.post(`/clientes/${id}/reset-password`, { nueva_password })
}

export async function eliminarCliente(id: string): Promise<void> {
  await apiClient.delete(`/clientes/${id}`)
}

export async function getCotizacionesCliente(id: string): Promise<Sesion[]> {
  const { data } = await apiClient.get<Sesion[]>(`/clientes/${id}/cotizaciones`)
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
