import axios from 'axios'
import { create } from 'zustand'
import * as authApi from '../api/auth'
import type { Usuario } from '../types/auth'

interface AuthState {
  usuario: Usuario | null
  token: string | null
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  initFromStorage: () => void
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  usuario: null,
  token: null,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const data = await authApi.login(email, password)
      // Persiste token y usuario en localStorage
      localStorage.setItem('yuda_token', data.access_token)
      localStorage.setItem('yuda_usuario', JSON.stringify(data.usuario))
      set({ usuario: data.usuario, token: data.access_token, isLoading: false })
    } catch (err) {
      // Toma el mensaje del backend si existe; si no, uno genérico en español
      let mensaje = 'No se pudo iniciar sesión'
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        mensaje = err.response.data.detail
      }
      set({ error: mensaje, isLoading: false })
    }
  },

  logout: () => {
    authApi.logout()
    set({ usuario: null, token: null, isLoading: false, error: null })
  },

  initFromStorage: () => {
    const token = localStorage.getItem('yuda_token')
    const usuarioRaw = localStorage.getItem('yuda_usuario')
    if (token && usuarioRaw) {
      set({ token, usuario: JSON.parse(usuarioRaw) as Usuario })
    }
  },

  clearError: () => set({ error: null }),
}))
