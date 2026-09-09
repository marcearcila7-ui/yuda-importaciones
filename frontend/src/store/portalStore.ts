import axios from 'axios'
import { create } from 'zustand'
import { loginPortal } from '../api/portal'
import { tokenVencido } from '../lib/jwt'
import type { ClientePortal } from '../types/portal'

interface PortalState {
  cliente: ClientePortal | null
  token: string | null
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  initFromStorage: () => void
  clearError: () => void
}

export const usePortalStore = create<PortalState>((set) => ({
  cliente: null,
  token: null,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const data = await loginPortal(email, password)
      localStorage.setItem('yuda_portal_token', data.access_token)
      localStorage.setItem('yuda_portal_cliente', JSON.stringify(data.cliente))
      set({ cliente: data.cliente, token: data.access_token, isLoading: false })
      return true
    } catch (err) {
      // Login fallido: limpiar cualquier sesión previa para no quedar como otro cliente.
      localStorage.removeItem('yuda_portal_token')
      localStorage.removeItem('yuda_portal_cliente')
      let mensaje = 'No se pudo iniciar sesión'
      if (axios.isAxiosError(err) && err.response?.data?.detail) {
        mensaje = err.response.data.detail
      }
      set({ cliente: null, token: null, error: mensaje, isLoading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('yuda_portal_token')
    localStorage.removeItem('yuda_portal_cliente')
    set({ cliente: null, token: null, isLoading: false, error: null })
  },

  initFromStorage: () => {
    const token = localStorage.getItem('yuda_portal_token')
    const clienteRaw = localStorage.getItem('yuda_portal_cliente')
    if (!token || !clienteRaw) return
    // Mismo arreglo que en authStore.ts: sin esto, un token vencido se
    // restauraba igual y el portal se rompía recién con la primera llamada.
    if (tokenVencido(token)) {
      localStorage.removeItem('yuda_portal_token')
      localStorage.removeItem('yuda_portal_cliente')
      return
    }
    set({ token, cliente: JSON.parse(clienteRaw) as ClientePortal })
  },

  clearError: () => set({ error: null }),
}))
