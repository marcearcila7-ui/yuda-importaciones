export interface OCRResultado {
  descripcion_es: string | null
  descripcion_en: string | null
  descripcion_zh: string | null
  material: string | null
  uso: string | null
  supplier_nombre: string | null
  supplier_numero: string | null
  price_rmb: number | null
  qty_por_ctn: number | null
  largo_cm: number | null
  ancho_cm: number | null
  alto_cm: number | null
  cbm_directo: number | null
  gw: number | null
  colores: string | null
  cantidad_minima: number | null
  notas: string | null
  confianza: 'alta' | 'media' | 'baja'
  // Calidad de la foto evaluada por el modelo. Puede faltar en ítems viejos.
  legible?: boolean
  motivo_ilegible?: string | null
}

export interface OCRResponse {
  foto_url: string
  datos_extraidos: OCRResultado
}
