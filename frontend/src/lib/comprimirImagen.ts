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

function reducir(file: File): Promise<File> {
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
      // Lado máximo que el modelo de visión aprovecha (Opus 5 lee hasta 2576px;
      // antes eran 1568 y por eso este valor estaba en 1600). Reducir más la foto
      // es tirar a la basura detalle que sirve para leer el chino manuscrito.
      const maxLado = 2576
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

// Una foto HEIC de iPhone. El canvas del navegador NO sabe decodificarla: el
// decode no dispara ni onload ni onerror, se come los 10 segundos del timeout y
// al final devuelve el original igual. Se detecta antes y se sube tal cual, que
// el backend la convierte a JPEG al recibirla.
function esHeic(file: File): boolean {
  return (
    file.type === 'image/heic' ||
    file.type === 'image/heif' ||
    /\.hei[cf]$/i.test(file.name)
  )
}

export async function comprimirImagen(file: File): Promise<File> {
  // El HEIC no pasa por el canvas: el navegador no lo sabe abrir.
  if (esHeic(file)) return file
  // Atajo solo si ya es liviana Y viene con un tipo que el backend acepta.
  // Si el tipo es dudoso hay que pasarla por el canvas aunque sea pequeña.
  if (file.size < 1_500_000 && TIPOS_OK.has(file.type)) return file
  return reducir(file)
}
