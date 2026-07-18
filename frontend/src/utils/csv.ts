// Exporta filas a un archivo .csv y dispara la descarga en el navegador.
// Incluye BOM para que Excel abra los acentos correctamente.

export interface ColumnaCSV {
  key: string
  label: string
}

export function descargarCSV(
  nombre: string,
  filas: Array<Record<string, string | number | boolean | null | undefined>>,
  columnas?: ColumnaCSV[],
): void {
  if (!filas.length) return
  const cols = columnas ?? Object.keys(filas[0]).map((k) => ({ key: k, label: k }))

  const escapar = (v: unknown): string => {
    const s = v == null ? '' : String(v)
    return /[",\n\r;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }

  const encabezado = cols.map((c) => escapar(c.label)).join(',')
  const cuerpo = filas.map((f) => cols.map((c) => escapar(f[c.key])).join(',')).join('\r\n')
  const csv = '﻿' + encabezado + '\r\n' + cuerpo

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre.endsWith('.csv') ? nombre : `${nombre}.csv`
  enlace.click()
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}
