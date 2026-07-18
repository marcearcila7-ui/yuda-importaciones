import axios from 'axios'
import { create } from 'zustand'
import * as authApi from '../api/auth'
import type { Usuario } from '../types/auth'

interface AuthState {
  usuario: Usuario | null
  token: string | null
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<boolean>
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
      return true
    } catch (err) {
      // Login fallido: limpiar CUALQUIER sesión previa para no quedar logueado con
      // otra cuenta (bug crítico si el token viejo seguía en localStorage).
      localStorage.removeItem('yuda_token')
      localStorage.removeItem('yuda_usuario')
      let mensaje = 'No se pudo iniciar sesión'
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        mensaje = err.response.data.detail
      }
      set({ usuario: null, token: null, error: mensaje, isLoading: false })
      return false
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
