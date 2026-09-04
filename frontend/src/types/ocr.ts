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
  // Recuadros en fracciones de 0 a 1: donde esta el cartel y donde el producto.
  recuadro_cartel?: number[] | null
  recuadro_producto?: number[] | null
  // Foto ya recortada al producto: es la que va a los documentos.
  foto_recorte_url?: string | null
  colores: string | null
  cantidad_minima: number | null
  // Minimo de compra de TODA la tienda. Solo llega cuando el cartel trae los dos
  // minimos; la app avisa y la vendedora elige cual usar. Falta en items viejos.
  cantidad_minima_tienda?: number | null
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
