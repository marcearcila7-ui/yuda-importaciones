import { create } from 'zustand'

export interface ConfirmOpts {
  mensaje: string
  titulo?: string
  textoConfirmar?: string
  textoCancelar?: string
  peligro?: boolean // botón de confirmar en rojo (acciones destructivas)
}

interface ConfirmState {
  abierto: boolean
  opts: ConfirmOpts | null
  _resolve: ((v: boolean) => void) | null
  pedir: (opts: ConfirmOpts) => Promise<boolean>
  responder: (v: boolean) => void
}

export const useConfirmStore = create<ConfirmState>((set, get) => ({
  abierto: false,
  opts: null,
  _resolve: null,
  pedir: (opts) =>
    new Promise<boolean>((resolve) => {
      set({ abierto: true, opts, _resolve: resolve })
    }),
  responder: (v) => {
    const r = get()._resolve
    set({ abierto: false, opts: null, _resolve: null })
    r?.(v)
  },
}))

// Helper imperativo, reemplazo directo de window.confirm:
//   if (await confirmar('¿Seguro?')) { ... }
//   if (await confirmar({ mensaje, peligro: true, textoConfirmar: 'Eliminar' })) { ... }
export const confirmar = (opts: ConfirmOpts | string): Promise<boolean> =>
  useConfirmStore.getState().pedir(typeof opts === 'string' ? { mensaje: opts } : opts)
