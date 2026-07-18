import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Download } from 'lucide-react'
import { getHistorial } from '../api/admin'
import { eliminarSesion } from '../api/packing'
import { useAuthStore } from '../store/authStore'
import { confirmar } from '../store/confirmStore'
import type { SesionHistorial } from '../types/admin'

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

function Historial() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { usuario } = useAuthStore()
  const esAdmin = usuario?.rol === 'admin'
  const [sesiones, setSesiones] = useState<SesionHistorial[]>([])
  const [cargando, setCargando] = useState(false)
  const [fechaDesde, setFechaDesde] = useState('')
  const [fechaHasta, setFechaHasta] = useState('')
  const [nombreCliente, setNombreCliente] = useState('')

  const buscar = async () => {
    setCargando(true)
    try {
      const data = await getHistorial({
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
        nombre_cliente: nombreCliente || undefined,
      })
      setSesiones(data)
    } finally {
      setCargando(false)
    }
  }

  // Exporta el historial visible a CSV (se abre en Excel/Sheets). Solo lo que
  // está cargado en pantalla, respetando los filtros aplicados.
  const exportarCsv = () => {
    if (sesiones.length === 0) return
    const cols = [
      t('historial.fecha'),
      t('historial.cliente'),
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

  const handleEliminar = async (s: SesionHistorial) => {
    const ok = await confirmar({
      mensaje: t('historial.confirmarEliminar', { cliente: s.nombre_cliente }),
      peligro: true,
      textoConfirmar: t('historial.eliminar'),
    })
    if (!ok) return
    try {
      await eliminarSesion(s.id)
      toast.success(t('historial.eliminada'))
      buscar()
    } catch {
      toast.error(t('historial.errorEliminar'))
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
        <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>{t('historial.titulo')}</h1>
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {fechaHoyTexto}
        </p>
      </div>

      {/* Filtros */}
      <div className="card flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('historial.fechaDesde')}
          <input type="date" value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('historial.fechaHasta')}
          <input type="date" value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
          {t('historial.cliente')}
          <input type="text" value={nombreCliente} onChange={(e) => setNombreCliente(e.target.value)} style={inputStyle} className={inputClase} />
        </label>
        <button
          type="button"
          onClick={buscar}
          disabled={cargando}
          className="font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          {t('historial.buscar')}
        </button>
        <button
          type="button"
          onClick={exportarCsv}
          disabled={sesiones.length === 0}
          className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: '#10B981', borderRadius: 8, padding: '0 20px', fontSize: 16 }}
        >
          <Download size={18} /> {t('historial.exportar')}
        </button>
      </div>

      {/* Tabla */}
      {sesiones.length === 0 ? (
        <p className="mt-6 text-center" style={{ color: '#6B7280' }}>
          {t('historial.sinResultados')}
        </p>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[720px] text-sm">
            <thead style={{ backgroundColor: '#0D0D0D', color: '#FFFFFF' }}>
              <tr>
                <th className="px-4 py-3 text-left font-semibold">{t('historial.fecha')}</th>
                <th className="px-4 py-3 text-left font-semibold">{t('historial.cliente')}</th>
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
                <tr key={s.id} style={{ backgroundColor: i % 2 === 0 ? '#FFFFFF' : '#F9F9F7' }}>
                  <td className="px-4 py-3">{s.fecha}</td>
                  <td className="px-4 py-3 font-medium">{s.nombre_cliente}</td>
                  <td className="px-4 py-3 text-right">{s.total_items}</td>
                  <td className="px-4 py-3 text-right">{s.total_rmb.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{s.total_usd.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{s.cantidad_proveedores}</td>
                  <td className="px-4 py-3">
                    <span
                      className="rounded-full px-3 py-1 text-xs font-semibold"
                      style={
                        s.tiene_pedidos
                          ? { backgroundColor: '#D1FAE5', color: '#065F46' }
                          : { backgroundColor: '#F3F4F6', color: '#6B7280' }
                      }
                    >
                      {s.tiene_pedidos ? t('historial.conPedidos') : t('historial.sinPedidos')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => navigate(`/cotizacion/${s.id}`)}
                        className="rounded-lg px-3 py-1 text-sm font-medium"
                        style={{ backgroundColor: '#EEF0FD', color: '#4B52E8' }}
                      >
                        {t('historial.verDetalle')}
                      </button>
                      {esAdmin && (
                        <button
                          type="button"
                          onClick={() => handleEliminar(s)}
                          className="rounded-lg px-3 py-1 text-sm font-medium"
                          style={{ backgroundColor: '#FEE2E2', color: '#EF4444' }}
                        >
                          {t('historial.eliminar')}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Historial
