// Decodifica el "exp" (vencimiento) de un JWT sin verificar la firma: eso ya lo
// hace el backend en cada request. Esto solo sirve para decidir, ANTES de
// mostrar nada, si vale la pena restaurar la sesión guardada o no.
export function tokenVencido(token: string): boolean {
  try {
    const payloadB64 = token.split('.')[1]
    const normalizado = payloadB64.replace(/-/g, '+').replace(/_/g, '/')
    const relleno = normalizado.padEnd(normalizado.length + ((4 - (normalizado.length % 4)) % 4), '=')
    const payload = JSON.parse(atob(relleno)) as { exp?: number }
    if (!payload.exp) return false
    return payload.exp * 1000 < Date.now()
  } catch {
    // Token corrupto/ilegible: mejor tratarlo como vencido que dejar pasar algo raro.
    return true
  }
}
