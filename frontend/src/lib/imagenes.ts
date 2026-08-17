// Qué acepta un input de archivo de fotos.
//
// Se listan las extensiones además de los MIME a propósito: en Android el selector
// entrega muchas fotos con el type vacío o como "application/octet-stream" (galería
// de Google Fotos, Drive, imágenes recibidas por WhatsApp). Filtrando solo por MIME,
// esas fotos aparecían grises en el selector o se descartaban sin avisar.
export const ACCEPT_IMAGENES =
  'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'

// Timeout de las subidas de foto. Sin él, una subida estancada (pasa seguido con
// el 4G del mercado) se quedaba colgada para siempre en vez de fallar y poder reintentar.
export const TIMEOUT_SUBIDA = 120_000
