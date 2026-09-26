// Casilla numérica: selecciona todo su contenido al enfocarla, así basta con
// escribir el número nuevo, sin pelear con un valor (ej. un "0") que quedaba
// pegado adelante si se empezaba a escribir sin borrarlo primero a mano.
export function enfocarNumero(e: React.FocusEvent<HTMLInputElement>): void {
  e.currentTarget.select()
}
