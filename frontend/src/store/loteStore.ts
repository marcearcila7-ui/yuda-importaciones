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

// Foto elegida pero aún NO subida: se acumula en la fase de selección hasta que
// la vendedora pulsa "Procesar". `preview` es un object URL para la miniatura.
export interface FotoStaged {
  id: string
  file: File
  preview: string
}

type Fase = 'idle' | 'seleccion' | 'subiendo' | 'procesando' | 'completado'

const CONCURRENCIA = 4

interface LoteState {
  fase: Fase
  sesionId: string | null
  loteId: string | null
  seleccionadas: FotoStaged[]
  subidas: number
  totalSubir: number
  procesadas: number
  totalProc: number
  resultados: ResultadoLote[]
  errores: number
  erroresSubida: number
  agregarSeleccion: (sesionId: string, files: File[]) => void
  quitarSeleccion: (id: string) => void
  cancelarSeleccion: () => void
  procesarSeleccion: () => Promise<void>
  agregarMas: (files: File[]) => Promise<void>
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

// Libera los object URLs de las miniaturas para no filtrar memoria
const revocarPreviews = (fotos: FotoStaged[]) => fotos.forEach((f) => URL.revokeObjectURL(f.preview))

const ESTADO_INICIAL = {
  fase: 'idle' as Fase,
  sesionId: null,
  loteId: null,
  seleccionadas: [] as FotoStaged[],
  subidas: 0,
  totalSubir: 0,
  procesadas: 0,
  totalProc: 0,
  resultados: [] as ResultadoLote[],
  errores: 0,
  erroresSubida: 0,
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

  // Sube un conjunto de fotos (comprimidas) a un lote, en paralelo. Cuenta las
  // que fallan en `erroresSubida` para no perderlas en silencio.
  const subirFotos = async (loteId: string, files: File[]) => {
    let idx = 0
    const worker = async () => {
      while (idx < files.length) {
        const f = files[idx++]
        let ok = false
        try {
          const comprimido = await comprimirImagen(f)
          await subirFotoLote(loteId, comprimido)
          ok = true
        } catch {
          // no se pudo subir esta foto (red/servidor): se cuenta como error
        }
        set((s) => ({
          subidas: s.subidas + 1,
          erroresSubida: ok ? s.erroresSubida : s.erroresSubida + 1,
        }))
      }
    }
    await Promise.all(Array.from({ length: Math.min(CONCURRENCIA, files.length) }, worker))
  }

  return {
    ...ESTADO_INICIAL,

    // Acumula fotos en la lista de selección (sin subir ni procesar todavía).
    agregarSeleccion: (sesionId, files) => {
      if (files.length === 0) return
      const nuevas: FotoStaged[] = files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        preview: URL.createObjectURL(file),
      }))
      set((s) => ({
        fase: 'seleccion',
        sesionId: s.sesionId ?? sesionId,
        seleccionadas: [...s.seleccionadas, ...nuevas],
      }))
    },

    // Quita una foto de la selección (antes de procesar).
    quitarSeleccion: (id) =>
      set((s) => {
        const obj = s.seleccionadas.find((x) => x.id === id)
        if (obj) URL.revokeObjectURL(obj.preview)
        return { seleccionadas: s.seleccionadas.filter((x) => x.id !== id) }
      }),

    // Descarta toda la selección y vuelve al inicio.
    cancelarSeleccion: () =>
      set((s) => {
        revocarPreviews(s.seleccionadas)
        return { ...ESTADO_INICIAL, sesionId: s.sesionId }
      }),

    // Sube TODAS las fotos seleccionadas y dispara el OCR de una vez.
    procesarSeleccion: async () => {
      const { seleccionadas, sesionId } = get()
      if (!sesionId || seleccionadas.length === 0) return
      detenerPoll()
      const files = seleccionadas.map((x) => x.file)
      // Transición inmediata a "subiendo" para que la UI responda al toque
      set({
        fase: 'subiendo',
        subidas: 0,
        totalSubir: files.length,
        procesadas: 0,
        totalProc: 0,
        resultados: [],
        errores: 0,
        erroresSubida: 0,
      })
      // Limpiar un lote previo de la sesión, si quedó
      try {
        const prev = await loteActivo(sesionId)
        if (prev.lote_id) await borrarLote(prev.lote_id)
      } catch {
        // sin lote previo
      }
      const { lote_id } = await crearLote(sesionId)
      set({ loteId: lote_id })

      await subirFotos(lote_id, files)
      // Ya subidas: liberar las miniaturas y vaciar la selección
      revocarPreviews(seleccionadas)
      set({ seleccionadas: [] })

      await procesarLoteApi(lote_id)
      set({ fase: 'procesando', procesadas: 0, totalProc: files.length })
      iniciarPoll(lote_id)
    },

    // Suma más fotos al MISMO lote en revisión, sin perder lo ya procesado.
    // Sube las nuevas (quedan 'pendiente'), redispara el OCR (solo procesa las
    // pendientes) y al volver a 'completado' la lista incluye viejas + nuevas.
    agregarMas: async (files) => {
      const loteId = get().loteId
      if (!loteId || files.length === 0) return
      detenerPoll()
      set({ fase: 'subiendo', subidas: 0, totalSubir: files.length, erroresSubida: 0 })
      await subirFotos(loteId, files)
      await procesarLoteApi(loteId)
      set({ fase: 'procesando' })
      iniciarPoll(loteId)
    },

    retomar: async (sesionId) => {
      const actual = get()
      // Si ya estamos mostrando/armando el lote de ESTA misma cotización, no rehacer
      if (actual.fase !== 'idle' && actual.sesionId === sesionId) return
      // Cambió de cotización (o primera vez): limpiar lo que haya quedado del
      // lote anterior (evita que se mezclen productos de otro cliente) y fijar la sesión
      detenerPoll()
      revocarPreviews(actual.seleccionadas)
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
      revocarPreviews(get().seleccionadas)
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
