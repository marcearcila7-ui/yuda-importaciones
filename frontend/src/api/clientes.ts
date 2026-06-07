import apiClient from './client'
import type { Cliente, ClienteCreado, ClienteCreate } from '../types/cliente'
import type { Sesion } from '../types/packing'
import type { Seguimiento, SeguimientoUpdate } from '../types/seguimiento'

// El interceptor de token (yuda_token) ya está registrado en api/admin.ts

export async function getClientes(): Promise<Cliente[]> {
  const { data } = await apiClient.get<Cliente[]>('/clientes')
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
