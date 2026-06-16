import type { OCRResultado } from '../types/ocr'

// Datos obligatorios que la foto DEBE traer para poder usarse.
// Si falta cualquiera, la foto se considera no legible y hay que volver a tomarla.
// clave: campo del resultado · i18n: clave de traducción para nombrar el dato faltante
export const CAMPOS_OBLIGATORIOS: Array<{ clave: keyof OCRResultado; i18n: string }> = [
  { clave: 'price_rmb', i18n: 'precioRMB' },
  { clave: 'qty_por_ctn', i18n: 'unidPorCaja' },
  { clave: 'cbm_directo', i18n: 'cbm' },
  { clave: 'cantidad_minima', i18n: 'mqt' },
  { clave: 'supplier_nombre', i18n: 'proveedor' },
]

export interface Legibilidad {
  // true = la foto sirve; false = hay que volver a tomarla
  ok: boolean
  // true cuando el modelo marcó la imagen como ilegible (borrosa, sobreexpuesta, etc.)
  imagenIlegible: boolean
  // motivo crudo que devolvió el modelo (borrosa, sobreexpuesta, oscura...) o null
  motivo: string | null
  // claves i18n de los datos obligatorios que faltan
  faltantes: string[]
}

// Un campo cuenta como "faltante" si es null, undefined o cadena vacía.
function falta(valor: unknown): boolean {
  return valor === null || valor === undefined || valor === ''
}

// Evalúa si una foto es legible y trae todos los datos obligatorios.
export function evaluarLegibilidad(datos: OCRResultado): Legibilidad {
  // legible puede venir undefined en ítems viejos: en ese caso no lo tratamos
  // como ilegible y dejamos que mande la validación de datos obligatorios.
  const imagenIlegible = datos.legible === false
  const faltantes = CAMPOS_OBLIGATORIOS.filter((c) => falta(datos[c.clave])).map((c) => c.i18n)
  return {
    ok: !imagenIlegible && faltantes.length === 0,
    imagenIlegible,
    motivo: datos.motivo_ilegible ?? null,
    faltantes,
  }
}
