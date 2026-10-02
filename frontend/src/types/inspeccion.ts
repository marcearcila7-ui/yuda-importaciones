// Versión de solo lectura para la vendedora/Marcela: "lo que llegó" según
// bodega, sin depender de descargar el Excel/PDF para revisarlo. El mismo
// shape que usa Yuda Logistic (bodega), pero acá nunca se guarda nada.

export interface CampoInspeccion {
  original: string | number | null
  corregido: string | number | null
}

// Caja fuera de lo uniforme (ej. llegó 1 caja de 50 uds además de las 3 de
// 100): se suma a `cajas` del ítem, no lo reemplaza.
export interface CajaExtra {
  ctns: number
  qty_por_ctn: number
  largo_cm: number | null
  ancho_cm: number | null
  alto_cm: number | null
  gw: number | null
}

export interface InspeccionItem {
  item_id: string
  // Foto con la que se cotizó (la del catálogo/proveedor), para comparar
  // lado a lado contra `fotos` (la evidencia real que subió bodega).
  foto_url: string | null
  foto_final_url: string | null
  // Tienda de este producto: PedidoGenerado.supplier ES supplier_nombre (ver
  // agrupar_items_por_supplier en el backend), así se agrupan los productos
  // bajo la orden a la que pertenecen. supplier_numero quedó solo para leer
  // cotizaciones viejas, de cuando la clave era "tienda_stand".
  supplier_nombre: string | null
  supplier_numero: string | null
  referencia: CampoInspeccion
  descripcion_es: CampoInspeccion
  descripcion_en: CampoInspeccion
  cajas: CampoInspeccion
  uds_caja: CampoInspeccion
  largo_cm: CampoInspeccion
  ancho_cm: CampoInspeccion
  alto_cm: CampoInspeccion
  peso: CampoInspeccion
  referencia_coincide: boolean | null
  cajas_extra: CajaExtra[]
  sin_cajas_extra: boolean
  debe_devolver: boolean
  no_llego: boolean
  fotos: string[]
  video_url: string | null
}

export interface InspeccionSesion {
  sesion_id: string
  numero: string
  fecha: string
  items: InspeccionItem[]
}
