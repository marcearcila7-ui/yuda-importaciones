import { create } from 'zustand'
import { subirFotoOCR } from '../api/ocr'
import { comprimirImagen } from '../lib/comprimirImagen'
import type { OCRResultado } from '../types/ocr'

export interface ResultadoLote {
  id: string
  foto_url: string
  datos: OCRResultado
}

interface Fallida {
  nombre: string
  file: File
}

const CONCURRENCIA = 4
const REINTENTOS = 2

// Lee una foto con reintentos automáticos ante fallas transitorias
async function ocrConReintentos(file: File): Promise<ResultadoLote> {
  let ultimoError: unknown
  for (let intento = 0; intento <= REINTENTOS; intento++) {
    try {
      const comprimido = await comprimirImagen(file)
      const resp = await subirFotoOCR(comprimido)
      return { id: resp.foto_url, foto_url: resp.foto_url, datos: { ...resp.datos_extraidos } }
    } catch (e) {
      ultimoError = e
      await new Promise((r) => setTimeout(r, 800 * (intento + 1)))
    }
  }
  throw ultimoError
}

interface LoteState {
  procesando: boolean
  progreso: { hechas: number; total: number }
  resultados: ResultadoLote[]
  fallidas: Fallida[]
  procesarArchivos: (files: File[]) => Promise<void>
  reintentarFallidas: () => Promise<void>
  actualizarDato: (id: string, campo: keyof OCRResultado, valor: string | number | null) => void
  quitar: (id: string) => void
  limpiar: () => void
}

export const useLoteStore = create<LoteState>((set, get) => {
  // Procesa una lista de archivos en paralelo (cap CONCURRENCIA), agregando resultados al store
  const procesarPool = async (files: File[]) => {
    let idx = 0
    const worker = async () => {
      while (idx < files.length) {
        const f = files[idx++]
        try {
          const r = await ocrConReintentos(f)
          set((s) => ({ resultados: [...s.resultados, r] }))
        } catch {
          set((s) => ({ fallidas: [...s.fallidas, { nombre: f.name, file: f }] }))
        }
        set((s) => ({ progreso: { ...s.progreso, hechas: s.progreso.hechas + 1 } }))
      }
    }
    await Promise.all(Array.from({ length: Math.min(CONCURRENCIA, files.length) }, worker))
  }

  return {
    procesando: false,
    progreso: { hechas: 0, total: 0 },
    resultados: [],
    fallidas: [],

    // Procesa una tanda nueva; los resultados se ACUMULAN a los ya revisados
    procesarArchivos: async (files) => {
      if (files.length === 0) return
      set({ procesando: true, progreso: { hechas: 0, total: files.length } })
      await procesarPool(files)
      set({ procesando: false })
    },

    // Reintenta solo las fotos que habían fallado
    reintentarFallidas: async () => {
      const files = get().fallidas.map((f) => f.file)
      if (files.length === 0) return
      set({ fallidas: [], procesando: true, progreso: { hechas: 0, total: files.length } })
      await procesarPool(files)
      set({ procesando: false })
    },

    actualizarDato: (id, campo, valor) =>
      set((s) => ({
        resultados: s.resultados.map((r) =>
          r.id === id ? { ...r, datos: { ...r.datos, [campo]: valor } } : r,
        ),
      })),

    quitar: (id) => set((s) => ({ resultados: s.resultados.filter((r) => r.id !== id) })),

    limpiar: () => set({ resultados: [], fallidas: [], progreso: { hechas: 0, total: 0 }, procesando: false }),
  }
})
