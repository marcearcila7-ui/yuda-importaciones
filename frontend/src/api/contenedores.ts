import apiClient from './client'
import type { Contenedor, ContenedorCreate } from '../types/contenedor'

export async function getContenedores(): Promise<Contenedor[]> {
  const { data } = await apiClient.get<Contenedor[]>('/contenedores')
  return data
}

export async function crearContenedor(datos: ContenedorCreate): Promise<Contenedor> {
  const { data } = await apiClient.post<Contenedor>('/contenedores', datos)
  return data
}

export async function actualizarContenedor(
  id: string,
  datos: Partial<ContenedorCreate>,
): Promise<Contenedor> {
  const { data } = await apiClient.patch<Contenedor>(`/contenedores/${id}`, datos)
  return data
}

export async function eliminarContenedor(id: string): Promise<void> {
  await apiClient.delete(`/contenedores/${id}`)
}
