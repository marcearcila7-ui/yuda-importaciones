import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { Download, Trash2, X } from 'lucide-react'
import { getHistorial } from '../api/admin'
import { eliminarSesion } from '../api/packing'
import { confirmar } from '../store/confirmStore'
import Button from '../components/ui/Button'
import type { SesionHistorial } from '../types/admin'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[var(--yuda-primary)] focus:outline-none'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

// Lo que puede llegar por navegación desde el dashboard: "ver las cotizaciones
// de este mes" o "ver las cotizaciones de esta vendedora" sin tener que
// escribir los filtros a mano.
interface FiltrosDesdeNavegacion {
  fecha_desde?: string
  fecha_hasta?: string
  vendedora_id?: string
  vendedora_nombre?: string
}

function Historial() {
  const navigate = useNavigate()
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const estadoInicial = location.state as FiltrosDesdeNavegacion | null
  const [sesiones, setSesiones] = useState<SesionHistorial[]>([])
  const [seleccionadas, setSeleccionadas] = useState<Set<string>>(new Set())
  const [eliminando, setEliminando] = useState(false)
  const [cargando, setCargando] = useState(false)
  const [cargandoMas, setCargandoMas] = useState(false)
  const [hayMas, setHayMas] = useState(false)
  const [fechaDesde, setFechaDesde] = useState(estadoInicial?.fecha_desde || '')
  const [fechaHasta, setFechaHasta] = useState(estadoInicial?.fecha_hasta || '')
  const [nombreCliente, setNombreCliente] = useState('')
  // Filtro por vendedora: no tiene su propio input, solo llega desde "Por
  // vendedora" del dashboard. Se muestra como una etiqueta que se puede quitar.
  const [vendedoraFiltro, setVendedoraFiltro] = useState<{ id: string; nombre: string } | null>(
    estadoInicial?.vendedora_id
      ? { id: estadoInicial.vendedora_id, nombre: estadoInicial.vendedora_nombre || '' }
      : null,
  )

  // Cotizaciones por página; se piden de a tandas con "Cargar más" para no traer
  // cientos de golpe. Los filtros reinician a la primera página.
  const PAGINA = 50

  // Acepta un id de vendedora explícito para el caso de "quitar el filtro":
  // sin esto, limpiar el estado y buscar en el mismo clic seguía mandando el
  // filtro viejo (el cierre de la función no ve el setState hasta el próximo render).
  const buscar = async (vendedoraIdOverride?: string | null) => {
    setCargando(true)
    try {
      const data = await getHistorial({
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        nombre_cliente: nombreCliente || undefined,
        vendedora_id: (vendedoraIdOverride !== undefined ? vendedoraIdOverride : vendedoraFiltro?.id) || undefined,
        limit: PAGINA,
        offset: 0,
      })
      setSesiones(data)
      setHayMas(data.length === PAGINA)
      setSeleccionadas(new Set())
    } finally {
      setCargando(false)
    }
  }

  const quitarFiltroVendedora = () => {
    setVendedoraFiltro(null)
    buscar(null)
  }

  const cargarMas = async () => {
    setCargandoMas(true)
    try {
      const data = await getHistorial({
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        nombre_cliente: nombreCliente || undefined,
        vendedora_id: vendedoraFiltro?.id,
        limit: PAGINA,
        offset: sesiones.length,
      })
      setSesiones((prev) => [...prev, ...data])
      setHayMas(data.length === PAGINA)
    } finally {
      setCargandoMas(false)
    }
  }

  // Exporta el historial visible a CSV (se abre en Excel/Sheets). Solo lo que
  // está cargado en pantalla, respetando los filtros aplicados.
  const exportarCsv = () => {
    if (sesiones.length === 0) return
    const cols = [
      t('historial.fecha'),
      t('historial.cliente'),
      t('historial.vendedora'),
      t('historial.items'),
      t('historial.totalRmb'),
      t('historial.totalUsd'),
      t('historial.proveedores'),
      t('historial.pedidos'),
    ]
    const escapar = (v: string | number) => `"${String(v).replace(/"/g, '""')}"`
    const filas = sesiones.map((s) =>
      [
        s.fecha,
        s.nombre_cliente,
        s.vendedora_nombre || '',
        s.total_items,
        s.total_rmb.toFixed(2),
        s.total_usd.toFixed(2),
        s.cantidad_proveedores,
        s.tiene_pedidos ? t('historial.conPedidos') : t('historial.sinPedidos'),
      ]
        .map(escapar)
        .join(','),
    )
    // BOM para que Excel reconozca UTF-8 (acentos/ñ)
    const csv = '﻿' + [cols.map(escapar).join(','), ...filas].join('\r\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const enlace = document.createElement('a')
    enlace.href = url
    enlace.download = `historial_cotizaciones_${new Date().toISOString().slice(0, 10)}.csv`
    enlace.click()
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  }

  const toggleSeleccion = (id: string) => {
    setSeleccionadas((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const todoSeleccionado = sesiones.length > 0 && seleccionadas.size === sesiones.length

  const toggleSeleccionarTodo = () => {
    setSeleccionadas(todoSeleccionado ? new Set() : new Set(sesiones.map((s) => s.id)))
  }

  // Borra lo que esté marcado con el checkbox: una sola cotización o varias
  // a la vez. Si alguna no se pudo borrar (p. ej. tiene movimientos de cuenta),
  // se avisa cuál y por qué, en vez de fallar todo el lote en silencio.
  const handleEliminarSeleccionadas = async () => {
    const idsAEliminar = sesiones.filter((s) => seleccionadas.has(s.id))
    if (idsAEliminar.length === 0) return
    const ok = await confirmar({
      mensaje:
        idsAEliminar.length === 1
          ? t('historial.confirmarEliminar', { cliente: idsAEliminar[0].nombre_cliente })
          : t('historial.confirmarEliminarVarias', { cantidad: idsAEliminar.length }),
      peligro: true,
      textoConfirmar: t('historial.eliminar'),
    })
    if (!ok) return

    setEliminando(true)
    try {
      const resultados = await Promise.allSettled(idsAEliminar.map((s) => eliminarSesion(s.id)))
      const fallidas: string[] = []
      resultados.forEach((r, i) => {
        if (r.status === 'rejected') {
          const detalle = axios.isAxiosError(r.reason) ? r.reason.response?.data?.detail : null
          fallidas.push(
            `${idsAEliminar[i].nombre_cliente}: ${typeof detalle === 'string' ? detalle : t('historial.errorEliminar')}`,
          )
        }
      })
      const exitosas = idsAEliminar.length - fallidas.length
      if (exitosas > 0) {
        toast.success(exitosas === 1 ? t('historial.eliminada') : t('historial.eliminadasVarias', { cantidad: exitosas }))
      }
      fallidas.forEach((msg) => toast.error(msg))
      buscar()
    } finally {
      setEliminando(false)
    }
  }

  // Cargar sin filtros al montar
  useEffect(() => {
    buscar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const fechaHoyTexto = (() => {
    const f = new Date().toLocaleDateString(LOCALES[i18n.language] || 'es-ES', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    })
    return f.charAt(0).toUpperCase() + f.slice(1)
  })()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>{t('historial.titulo')}</h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {fechaHoyTexto}
        </p>
      </div>

      {/* Filtro por vendedora: solo aparece si se llegó desde "Por vendedora" del dashboard */}
      {vendedoraFiltro && (
        <div
          className="flex w-fit items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold"
          style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
        >
          {t('historial.filtrandoPorVendedora', { nombre: vendedoraFiltro.nombre })}
          <button type="button" onClick={quitarFiltroVendedora} aria-label={t('historial.quitarFiltro')}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Filtros */}
      <div className="card flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('historial.fechaDesde')}
          <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('historial.fechaHasta')}
          <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('historial.cliente')}
          <input type="text" value={nombreCliente} onChange={(e) => setNombreCliente(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <button
          type="button"
          onClick={() => buscar()}
          disabled={cargando}
          className="font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          {t('historial.buscar')}
        </button>
        <button
          type="button"
          onClick={exportarCsv}
          disabled={sesiones.length === 0}
          className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: 'var(--yuda-success)', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          <Download size={18} /> {t('historial.exportar')}
        </button>
        {/* Solo aparece habilitado si hay algo marcado con el checkbox de la
            tabla; borra uno o varios de una vez, según lo que esté marcado. */}
        <button
          type="button"
          onClick={handleEliminarSeleccionadas}
          disabled={seleccionadas.size === 0 || eliminando}
          aria-label={t('historial.eliminarSeleccionadas', { cantidad: seleccionadas.size })}
          title={t('historial.eliminarSeleccionadas', { cantidad: seleccionadas.size })}
          className="flex items-center justify-center gap-2 font-semibold disabled:opacity-40"
          style={{
            minHeight: 48,
            minWidth: 48,
            backgroundColor: 'var(--yuda-error-soft)',
            color: 'var(--yuda-error)',
            borderRadius: 8,
            padding: '0 16px',
            fontSize: 16,
          }}
        >
          <Trash2 size={18} />
          {seleccionadas.size > 0 && seleccionadas.size}
        </button>
      </div>

      {/* Tabla */}
      {sesiones.length === 0 ? (
        <p className="mt-6 text-center" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('historial.sinResultados')}
        </p>
      ) : (
        <>
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[720px] text-sm">
            <thead style={{ backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' }}>
              <tr>
                <th className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={todoSeleccionado}
                    onChange={toggleSeleccionarTodo}
                    aria-label={t('historial.seleccionarTodo')}
                    className="h-4 w-4"
                  />
                </th>
                <th className="px-4 py-3 text-left font-semibold">{t('historial.fecha')}</th>
                <th className="px-4 py-3 text-left font-semibold">{t('historial.cliente')}</th>
                <th className="px-4 py-3 text-left font-semibold">{t('historial.vendedora')}</th>
                <th className="px-4 py-3 text-right font-semibold">{t('historial.items')}</th>
                <th className="px-4 py-3 text-right font-semibold">{t('historial.totalRmb')}</th>
                <th className="px-4 py-3 text-right font-semibold">{t('historial.totalUsd')}</th>
                <th className="px-4 py-3 text-right font-semibold">{t('historial.proveedores')}</th>
                <th className="px-4 py-3 text-left font-semibold">{t('historial.pedidos')}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {sesiones.map((s, i) => (
                <tr key={s.id} style={{ backgroundColor: i % 2 === 0 ? 'var(--yuda-white)' : '#F9F9F7' }}>
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={seleccionadas.has(s.id)}
                      onChange={() => toggleSeleccion(s.id)}
                      aria-label={t('historial.seleccionarFila', { cliente: s.nombre_cliente })}
                      className="h-4 w-4"
                    />
                  </td>
                  <td className="px-4 py-3">{s.fecha}</td>
                  <td className="px-4 py-3 font-medium">{s.nombre_cliente}</td>
                  <td className="px-4 py-3" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {s.vendedora_nombre || '—'}
                  </td>
                  <td className="px-4 py-3 text-right">{s.total_items}</td>
                  <td className="px-4 py-3 text-right">{s.total_rmb.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{s.total_usd.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{s.cantidad_proveedores}</td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-full px-3 py-1 text-xs font-semibold"
                      style={
                        s.tiene_pedidos
                          ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }
                          : { backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }
                      }
                    >
                      {s.tiene_pedidos ? t('historial.conPedidos') : t('historial.sinPedidos')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => navigate(`/cotizacion/${s.id}`)}
                      className="rounded-lg px-3 py-1 text-sm font-medium"
                      style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                    >
                      {t('historial.verDetalle')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {hayMas && (
          <div className="mt-4 flex justify-center">
            <Button variant="ghost" onClick={cargarMas} disabled={cargandoMas}>
              {cargandoMas ? t('historial.cargandoMas') : t('historial.cargarMas')}
            </Button>
          </div>
        )}
        </>
      )}
    </div>
  )
}

export default Historial
