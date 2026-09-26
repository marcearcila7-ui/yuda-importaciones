// Casilla numérica: selecciona todo su contenido al enfocarla, así basta con
// escribir el número nuevo, sin pelear con un valor (ej. un "0") que quedaba
// pegado adelante si se empezaba a escribir sin borrarlo primero a mano. El
// select() va en un requestAnimationFrame a propósito: si se llama directo
// en el focus, el mouseup del mismo clic (que llega DESPUÉS del focus) le
// gana y vuelve a colapsar la selección justo donde cayó el clic -por eso
// "escribir 17 sobre un 0" terminaba en "017" o "170" en vez de reemplazarlo.
export function enfocarNumero(e: React.FocusEvent<HTMLInputElement>): void {
  const input = e.currentTarget
  requestAnimationFrame(() => input.select())
}
