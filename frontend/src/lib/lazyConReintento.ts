import { lazy } from 'react'
import type { ComponentType } from 'react'

// Con el sitio deployándose seguido, quien deja la pestaña abierta de un
// deploy a otro tiene cargado un index.html viejo que apunta a archivos de
// chunk con nombres que ya no existen en el servidor (cada deploy los
// renombra). Al hacer clic en algo que recién ahí carga una pantalla nueva
// (ej. una notificación que lleva a /cotizacion/:id), el import() del chunk
// falla con 404 y esto pasaba por fuera del ciclo normal de React: no se
// veía ni el error boundary, quedaba en blanco. La solución estándar es
// recargar la página UNA vez para traer el index.html nuevo (con los
// nombres de chunk correctos) -con una bandera en sessionStorage para no
// quedar en loop si el fallo es por otra razón.
export function lazyConReintento<T extends ComponentType<unknown>>(cargar: () => Promise<{ default: T }>) {
  const clave = 'yuda_reintento_chunk'
  return lazy(async () => {
    try {
      const modulo = await cargar()
      // Si esta carga funcionó, un fallo futuro (otro deploy más adelante,
      // en la misma pestaña) merece su propio reintento, no encontrarse la
      // bandera ya usada de la vez anterior.
      sessionStorage.removeItem(clave)
      return modulo
    } catch (error) {
      if (!sessionStorage.getItem(clave)) {
        sessionStorage.setItem(clave, '1')
        window.location.reload()
        // Nunca se resuelve: la recarga ya está en marcha.
        return new Promise<{ default: T }>(() => {})
      }
      sessionStorage.removeItem(clave)
      throw error
    }
  })
}
