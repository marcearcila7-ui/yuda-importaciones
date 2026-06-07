import apiClient from './client'
import type { Notificacion } from '../types/notificacion'

// El interceptor de token (yuda_token) ya está registrado en api/admin.ts

export async function getNotificaciones(soloNoLeidas = false): Promise<Notificacion[]> {
  const { data } = await apiClient.get<Notificacion[]>('/notificaciones', {
    params: { solo_no_leidas: soloNoLeidas },
  })
  return data
}

export async function marcarLeida(id: string): Promise<void> {
  await apiClient.post(`/notificaciones/${id}/leer`)
}

export async function marcarTodasLeidas(): Promise<void> {
  await apiClient.post('/notificaciones/leer-todas')
}
