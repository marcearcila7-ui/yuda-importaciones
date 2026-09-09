import axios from 'axios'
import { create } from 'zustand'
import * as authApi from '../api/auth'
import { tokenVencido } from '../lib/jwt'
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
    if (!token || !usuarioRaw) return
    // Antes esto restauraba el token sin fijarse si ya había vencido (8h): la
    // app mostraba el panel completo por un instante y recién cuando la
    // primera llamada a la API fallaba con 401 (uno o dos segundos después,
    // tiempo real de red) cerraba la sesión. Se sentía como que la app "abría
    // bien y después se rompía sola". Ahora se chequea el vencimiento ANTES
    // de restaurar nada: una sesión vieja va directo al login, sin flash.
    if (tokenVencido(token)) {
      localStorage.removeItem('yuda_token')
      localStorage.removeItem('yuda_usuario')
      sessionStorage.setItem('yuda_sesion_vencida', '1')
      return
    }
    set({ token, usuario: JSON.parse(usuarioRaw) as Usuario })
  },

  clearError: () => set({ error: null }),
}))
