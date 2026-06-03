import apiClient from './client'
import type { TokenResponse, Usuario } from '../types/auth'

// Inicia sesión y devuelve el token con los datos del usuario
export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>('/auth/login', { email, password })
  return data
}

// Obtiene los datos del usuario autenticado usando su token
export async function getMe(token: string): Promise<Usuario> {
  const { data } = await apiClient.get<Usuario>('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return data
}

// Cierra sesión eliminando los datos guardados en localStorage
export function logout(): void {
  localStorage.removeItem('yuda_token')
  localStorage.removeItem('yuda_usuario')
}
