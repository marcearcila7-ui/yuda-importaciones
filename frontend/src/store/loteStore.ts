import { create } from 'zustand'
import {
  borrarLote,
  crearLote,
  estadoLote,
  loteActivo,
  procesarLoteApi,
  reprocesarLote,
  subirFotoLote,
  type LoteEstadoResp,
} from '../api/lotes'
import { comprimirImagen } from '../lib/comprimirImagen'
import type { OCRResultado } from '../types/ocr'

export interface ResultadoLote {
  id: string
  foto_url: string
  datos: OCRResultado
}

type Fase = 'idle' | 'subiendo' | 'procesando' | 'completado'

const CONCURRENCIA = 4

interface LoteState {
  fase: Fase
  sesionId: string | null
  loteId: string | null
  subidas: number
  totalSubir: number
  procesadas: number
  totalProc: number
  resultados: ResultadoLote[]
  errores: number
  iniciar: (sesionId: string, files: File[]) => Promise<void>
  retomar: (sesionId: string) => Promise<void>
  reintentar: () => Promise<void>
  actualizarDato: (id: string, campo: keyof OCRResultado, valor: string | number | null) => void
  quitar: (id: string) => void
  finalizar: () => Promise<void>
}

let pollTimer: ReturnType<typeof setInterval> | null = null
const detenerPoll = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const ESTADO_INICIAL = {
  fase: 'idle' as Fase,
  sesionId: null,
  loteId: null,
  subidas: 0,
  totalSubir: 0,
  procesadas: 0,
  totalProc: 0,
  resultados: [] as ResultadoLote[],
  errores: 0,
}

export const useLoteStore = create<LoteState>((set, get) => {
  // Vuelca el estado del servidor al store; si terminó, arma los resultados
  const aplicarEstado = (est: LoteEstadoResp) => {
    if (est.estado === 'completado') {
      const resultados = est.items
        .filter((i) => i.estado === 'ok' && i.datos)
        .map((i) => ({ id: i.id, foto_url: i.foto_url, datos: { ...(i.datos as OCRResultado) } }))
      const errores = est.items.filter((i) => i.estado === 'error').length
      set({ fase: 'completado', resultados, errores, procesadas: est.procesadas, totalProc: est.total })
    } else {
      set({ fase: 'procesando', procesadas: est.procesadas, totalProc: est.total })
    }
  }

  const iniciarPoll = (loteId: string) => {
    detenerPoll()
    pollTimer = setInterval(async () => {
      try {
        const est = await estadoLote(loteId)
        aplicarEstado(est)
        if (est.estado === 'completado') detenerPoll()
      } catch {
        // ignorar fallas transitorias de red
      }
    }, 3000)
  }

  return {
    ...ESTADO_INICIAL,

    iniciar: async (sesionId, files) => {
      if (files.length === 0) return
      detenerPoll()
      // Limpiar un lote previo de la sesión, si quedó
      try {
        const prev = await loteActivo(sesionId)
        if (prev.lote_id) await borrarLote(prev.lote_id)
      } catch {
        // sin lote previo
      }
      set({ ...ESTADO_INICIAL, sesionId, fase: 'subiendo', totalSubir: files.length })

      const { lote_id } = await crearLote(sesionId)
      set({ loteId: lote_id })

      // Subir las fotos (comprimidas) en paralelo
      let idx = 0
      const worker = async () => {
        while (idx < files.length) {
          const f = files[idx++]
          try {
            const comprimido = await comprimirImagen(f)
            await subirFotoLote(lote_id, comprimido)
          } catch {
            // foto que no se pudo subir: se omite
          }
          set((s) => ({ subidas: s.subidas + 1 }))
        }
      }
      await Promise.all(Array.from({ length: Math.min(CONCURRENCIA, files.length) }, worker))

      // Disparar el OCR en segundo plano y empezar a consultar
      await procesarLoteApi(lote_id)
      set({ fase: 'procesando', procesadas: 0, totalProc: files.length })
      iniciarPoll(lote_id)
    },

    retomar: async (sesionId) => {
      const actual = get()
      // Si ya estamos mostrando el lote de ESTA misma cotización, no rehacer
      if (actual.fase !== 'idle' && actual.sesionId === sesionId) return
      // Cambió de cotización (o primera vez): limpiar lo que haya quedado del
      // lote anterior (evita que se mezclen productos de otro cliente) y fijar la sesión
      detenerPoll()
      set({ ...ESTADO_INICIAL, sesionId })
      let resp
      try {
        resp = await loteActivo(sesionId)
      } catch {
        return
      }
      if (!resp.lote_id) return
      const loteId = resp.lote_id
      if (resp.estado === 'cargando') {
        // Lote abandonado durante la subida: limpiarlo
        try {
          await borrarLote(loteId)
        } catch {
          // ignorar
        }
        return
      }
      set({ loteId })
      try {
        const est = await estadoLote(loteId)
        aplicarEstado(est)
        if (est.estado !== 'completado') iniciarPoll(loteId)
      } catch {
        // ignorar
      }
    },

    reintentar: async () => {
      const loteId = get().loteId
      if (!loteId) return
      set({ fase: 'procesando' })
      try {
        await reprocesarLote(loteId)
        iniciarPoll(loteId)
      } catch {
        // ignorar
      }
    },

    actualizarDato: (id, campo, valor) =>
      set((s) => ({
        resultados: s.resultados.map((r) =>
          r.id === id ? { ...r, datos: { ...r.datos, [campo]: valor } } : r,
        ),
      })),

    quitar: (id) => set((s) => ({ resultados: s.resultados.filter((r) => r.id !== id) })),

    finalizar: async () => {
      detenerPoll()
      const loteId = get().loteId
      if (loteId) {
        try {
          await borrarLote(loteId)
        } catch {
          // ignorar
        }
      }
      set({ ...ESTADO_INICIAL })
    },
  }
})
