import apiClient from './client'

export interface PushSubscriptionInput {
  endpoint: string
  p256dh: string
  auth: string
}

export async function getVapidPublicKey(): Promise<string> {
  const { data } = await apiClient.get<{ public_key: string }>('/push/vapid-public-key')
  return data.public_key
}

export async function suscribirPush(datos: PushSubscriptionInput): Promise<void> {
  await apiClient.post('/push/suscribir', datos)
}

export async function desuscribirPush(endpoint: string): Promise<void> {
  await apiClient.post('/push/desuscribir', { endpoint })
}
