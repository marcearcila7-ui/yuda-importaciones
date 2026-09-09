import axios from 'axios'
import { create } from 'zustand'
import * as packingApi from '../api/packing'
import type { ItemCreate, ItemResponse, Sesion } from '../types/packing'

interface PackingState {
  sesiones: Sesion[]
  sesionActual: Sesion | null
  items: ItemResponse[]
  isLoading: boolean
  error: string | null
  cargarSesiones: () => Promise<void>
  crearSesion: (
    nombre_cliente: string,
    tipo_cambio_usd?: number,
    cliente_id?: string | null,
    tipo_cotizacion?: 'productos' | 'bolsos',
  ) => Promise<void>
  seleccionarSesion: (sesion: Sesion) => Promise<void>
  cargarItems: () => Promise<void>
  agregarItem: (data: ItemCreate) => Promise<void>
  actualizarItem: (item_id: string, data: Partial<ItemCreate>) => Promise<void>
  eliminarItem: (item_id: string) => Promise<void>
  volverAlInicio: () => void
  clearError: () => void
}

// Extrae un mensaje de error legible en español
function mensajeError(err: unknown, generico: string): string {
  if (axios.isAxiosError(err) && err.response?.data?.detail) {
    return err.response.data.detail
  }
  return generico
}

export const usePackingStore = create<PackingState>((set, get) => ({
  sesiones: [],
  sesionActual: null,
  items: [],
  isLoading: false,
  error: null,

  cargarSesiones: async () => {
    set({ isLoading: true, error: null })
    try {
      const sesiones = await packingApi.getSesiones()
      set({ sesiones, isLoading: false })
    } catch (err) {
      set({ error: mensajeError(err, 'No se pudieron cargar las cotizaciones'), isLoading: false })
    }
  },

  crearSesion: async (nombre_cliente, tipo_cambio_usd, cliente_id, tipo_cotizacion) => {
    set({ isLoading: true, error: null })
    try {
      const sesion = await packingApi.crearSesion({
        nombre_cliente,
        tipo_cambio_usd,
        cliente_id,
        tipo_cotizacion,
      })
      set((s) => ({
        sesiones: [sesion, ...s.sesiones],
        sesionActual: sesion,
        items: [],
        isLoading: false,
      }))
    } catch (err) {
      set({ error: mensajeError(err, 'No se pudo crear la cotización'), isLoading: false })
    }
  },

  seleccionarSesion: async (sesion) => {
    set({ sesionActual: sesion })
    await get().cargarItems()
  },

  cargarItems: async () => {
    const sesion = get().sesionActual
    if (!sesion) return
    set({ isLoading: true, error: null })
    try {
      const items = await packingApi.getItems(sesion.id)
      set({ items, isLoading: false })
    } catch (err) {
      set({ error: mensajeError(err, 'No se pudieron cargar los ítems'), isLoading: false })
    }
  },

  agregarItem: async (data) => {
    const sesion = get().sesionActual
    if (!sesion) return
    set({ error: null })
    try {
      const item = await packingApi.crearItem(sesion.id, data)
      set((s) => ({ items: [...s.items, item] }))
    } catch (err) {
      set({ error: mensajeError(err, 'No se pudo agregar el ítem') })
    }
  },

  actualizarItem: async (item_id, data) => {
    const sesion = get().sesionActual
    if (!sesion) return
    set({ error: null })
    try {
      const actualizado = await packingApi.actualizarItem(sesion.id, item_id, data)
      set((s) => ({ items: s.items.map((i) => (i.id === item_id ? actualizado : i)) }))
    } catch (err) {
      set({ error: mensajeError(err, 'No se pudo actualizar el ítem') })
    }
  },

  eliminarItem: async (item_id) => {
    const sesion = get().sesionActual
    if (!sesion) return
    set({ error: null })
    try {
      await packingApi.eliminarItem(sesion.id, item_id)
      set((s) => ({ items: s.items.filter((i) => i.id !== item_id) }))
    } catch (err) {
      set({ error: mensajeError(err, 'No se pudo eliminar el ítem') })
    }
  },

  // Cierra la cotización actual y vuelve a la pantalla de inicio
  volverAlInicio: () => set({ sesionActual: null, items: [], error: null }),

  clearError: () => set({ error: null }),
}))
