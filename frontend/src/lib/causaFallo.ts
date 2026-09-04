import axios from 'axios'

export type CausaFallo = 'servidor' | 'conexion'

// Distingue una falla NUESTRA de una falla de la conexion de la vendedora.
//
// Importa mucho para el mensaje: si el servidor respondio con un error, el
// problema es del sistema y volver a tomar las fotos no arregla nada; pedirselo
// es mandarla a repetir trabajo al pedo, como paso el 15-ago-2026 cuando la app
// dijo "foto no legible, vuelve a tomarla" 268 veces porque la cuenta del OCR se
// habia quedado sin saldo. Si no hubo respuesta, ahi si es la red y reintentar sirve.
export function causaDelFallo(err: unknown): CausaFallo {
  if (axios.isAxiosError(err) && err.response) return 'servidor'
  return 'conexion'
}
