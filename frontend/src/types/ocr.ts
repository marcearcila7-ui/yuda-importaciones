export interface OCRResultado {
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
  descripcion_zh: string | null
  notas: string | null
  confianza: 'alta' | 'media' | 'baja'
}

export interface OCRResponse {
  foto_url: string
  datos_extraidos: OCRResultado
}
