// Los celulares chinos tienen 11 dígitos y empiezan por 1 (13x, 15x, 18x...).
// El OCR usa el teléfono de la tarjeta de presentación como reemplazo del N°
// Stand cuando la foto no tiene cartel de tienda (ver el prompt en
// ocr_service.py): esto detecta ese caso para avisarlo en la UI, no cambia
// lo que ya extrae el OCR.
export function pareceTelefono(numero: string | null | undefined): boolean {
  if (!numero) return false
  return /^1[3-9]\d{9}$/.test(numero.trim())
}
