// Comprime/reduce una imagen antes de subir (las fotos de celular pesan mucho).
// Reescala a un lado máximo de 1600px y reencoda a JPEG. Si algo falla, devuelve el original.
//
// Además de aligerar, sirve para NORMALIZAR el tipo: en Android el selector de
// archivos entrega muchas fotos con el type vacío o "application/octet-stream"
// (galería de Google Fotos, imágenes recibidas por WhatsApp, Drive), y el backend
// solo acepta image/jpeg, image/png o image/webp. Al pasarlas por el canvas salen
// siempre como JPEG de verdad.

// Tipos que el backend acepta tal cual (ver backend/app/api/routes/ocr.py)
const TIPOS_OK = new Set(['image/jpeg', 'image/png', 'image/webp'])

// Si el navegador no decodifica la foto en este tiempo, se sigue con el original.
// En Android con poca memoria y fotos de muchos megapíxeles, el decode a veces no
// dispara ni onload ni onerror y la promesa se quedaba colgada para siempre.
const TIMEOUT_MS = 10_000

// Lado máximo que el modelo de visión aprovecha (Opus 5 lee hasta 2576px;
// antes eran 1568 y por eso este valor estaba en 1600). Reducir más la foto
// es tirar a la basura detalle que sirve para leer el chino manuscrito.
const LADO_MAX_OCR = 2576

// Fotos de detalle del bolso (interior/herrajes/riata/exterior): nadie las lee
// con OCR, solo se ven en el PDF/Excel a tamaño de miniatura. Antes se les
// aplicaba el mismo lado de 2576px que a la foto del cartel y por eso tardaban
// varias veces más en subir (fotos de celular de 12+ MP) sin ninguna ganancia
// visual. Con este tope quedan livianas y la subida es casi instantánea.
const LADO_MAX_DETALLE = 1000

function reducir(file: File, maxLado: number): Promise<File> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file)
    let resuelto = false

    const terminar = (resultado: File) => {
      if (resuelto) return
      resuelto = true
      clearTimeout(temporizador)
      URL.revokeObjectURL(url)
      resolve(resultado)
    }

    const temporizador = setTimeout(() => terminar(file), TIMEOUT_MS)

    const img = new Image()
    img.onload = () => {
      let { width, height } = img
      if (Math.max(width, height) > maxLado) {
        const escala = maxLado / Math.max(width, height)
        width = Math.round(width * escala)
        height = Math.round(height * escala)
      }
      const canvas = document.createElement('canvas')
      canvas.width = width
      canvas.height = height
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        terminar(file)
        return
      }
      ctx.drawImage(img, 0, 0, width, height)
      canvas.toBlob(
        (blob) => {
          if (!blob) {
            terminar(file)
            return
          }
          const nombre = file.name.replace(/\.[^.]+$/, '') + '.jpg'
          terminar(new File([blob], nombre, { type: 'image/jpeg' }))
        },
        'image/jpeg',
        0.85,
      )
    }
    img.onerror = () => terminar(file)
    img.src = url
  })
}

// Una foto HEIC de iPhone. El canvas del navegador NO sabe decodificarla
// directo: el decode no dispara ni onload ni onerror. Por eso se pasa antes
// por heic2any (WASM de libheif), que sí la decodifica, y de ahí el resultado
// entra al mismo pipeline de `reducir` de siempre.
function esHeic(file: File): boolean {
  return (
    file.type === 'image/heic' ||
    file.type === 'image/heif' ||
    /\.hei[cf]$/i.test(file.name)
  )
}

// Si heic2any no termina en este tiempo (celular viejo, poca memoria), se
// sube el HEIC tal cual: el backend igual la convierte a JPEG al recibirla,
// solo que llega más pesada. Mejor eso que quedarse colgada.
const TIMEOUT_HEIC_MS = 15_000

async function decodificarHeic(file: File): Promise<File> {
  const heic2any = (await import('heic2any')).default
  const resultado = await heic2any({ blob: file, toType: 'image/jpeg', quality: 0.92 })
  const blob = Array.isArray(resultado) ? resultado[0] : resultado
  const nombre = file.name.replace(/\.[^.]+$/, '') + '.jpg'
  return new File([blob], nombre, { type: 'image/jpeg' })
}

async function comprimir(file: File, maxLado: number, atajoBytes: number): Promise<File> {
  if (esHeic(file)) {
    try {
      const jpeg = await Promise.race([
        decodificarHeic(file),
        new Promise<never>((_, reject) => setTimeout(() => reject(new Error('timeout heic')), TIMEOUT_HEIC_MS)),
      ])
      // Ya es un JPEG normal: pasa por el mismo redimensionado que las demás.
      return reducir(jpeg, maxLado)
    } catch {
      return file
    }
  }
  // Atajo solo si ya es liviana Y viene con un tipo que el backend acepta.
  // Si el tipo es dudoso hay que pasarla por el canvas aunque sea pequeña.
  if (file.size < atajoBytes && TIPOS_OK.has(file.type)) return file
  return reducir(file, maxLado)
}

// Foto del cartel/producto que lee el OCR: necesita resolución alta para que
// el modelo distinga el chino manuscrito.
export async function comprimirImagen(file: File): Promise<File> {
  return comprimir(file, LADO_MAX_OCR, 1_500_000)
}

// Foto de detalle del bolso (interior/herrajes/riata/exterior): nadie la lee,
// solo se ve en el PDF/Excel. Se prioriza velocidad de subida sobre nitidez.
export async function comprimirFotoDetalle(file: File): Promise<File> {
  return comprimir(file, LADO_MAX_DETALLE, 400_000)
}
