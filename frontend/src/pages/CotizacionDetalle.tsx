import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ArrowLeft, Building2, Coins, DollarSign, FileSpreadsheet, FileText, Mail, Package, Pencil, Phone, Store } from 'lucide-react'
import MetricCard from '../components/MetricCard'
import SeguimientoTimeline from '../components/portal/SeguimientoTimeline'
import { exportarCotizacionExcel, exportarCotizacionPDF, getItems, getSesiones } from '../api/packing'
import { getCliente, getSeguimiento } from '../api/clientes'
import { useAuthStore } from '../store/authStore'
import type { ItemResponse, Sesion } from '../types/packing'
import type { Cliente } from '../types/cliente'
import type { Seguimiento } from '../types/seguimiento'

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

// Vista de solo lectura de una cotización para la contadora y el admin (desde el
// historial). Muestra los productos, los totales, la ficha del cliente y el
// estado del envío (tracking/BL, con la evidencia de cada etapa). Marcela puede
// descargar el PDF/Excel de la cotización desde aquí.
function CotizacionDetalle() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const esAdmin = useAuthStore((s) => s.usuario?.rol === 'admin')
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [items, setItems] = useState<ItemResponse[]>([])
  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [seguimiento, setSeguimiento] = useState<Seguimiento | null>(null)
  const [cargando, setCargando] = useState(true)
  const [idioma, setIdioma] = useState<string>(['es', 'en', 'zh'].includes(i18n.language) ? i18n.language : 'es')
  const [generando, setGenerando] = useState<'pdf' | 'excel' | null>(null)

  useEffect(() => {
    let activo = true
    const cargar = async () => {
      setCargando(true)
      try {
        const [sesiones, itemsData, seg] = await Promise.all([
          getSesiones(),
          getItems(id),
          getSeguimiento(id).catch(() => null),
        ])
        if (!activo) return
        const s = sesiones.find((x) => x.id === id) ?? null
        setSesion(s)
        setItems(itemsData)
        setSeguimiento(seg)
        if (s?.cliente_id) {
          const c = await getCliente(s.cliente_id).catch(() => null)
          if (activo) setCliente(c)
        }
      } finally {
        if (activo) setCargando(false)
      }
    }
    cargar()
    return () => {
      activo = false
    }
  }, [id])

  const totales = useMemo(() => {
    const totalRmb = items.reduce((acc, i) => acc + (i.total_rmb || 0), 0)
    const totalUsd = items.reduce((acc, i) => acc + (i.total_usd || 0), 0)
    const proveedores = new Set(items.map((i) => i.supplier_nombre).filter(Boolean)).size
    return { totalRmb, totalUsd, proveedores }
  }, [items])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  // Descarga el PDF/Excel de la cotización (Safari: abrir la pestaña dentro del toque).
  const descargar = async (tipo: 'pdf' | 'excel') => {
    setGenerando(tipo)
    const ventana = window.open('', '_blank')
    try {
      const blob = tipo === 'pdf' ? await exportarCotizacionPDF(id, idioma) : await exportarCotizacionExcel(id, idioma)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = `Cotizacion_${sesion?.nombre_cliente ?? ''}_${idioma}.${tipo === 'pdf' ? 'pdf' : 'xlsx'}`
        a.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      ventana?.close()
      toast.error(t('detalle.errorDescargar'))
    } finally {
      setGenerando(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => navigate('/historial')}
          className="flex items-center gap-2 text-sm font-medium"
          style={{ color: '#4B52E8' }}
        >
          <ArrowLeft size={16} /> {t('detalle.volver')}
        </button>
        {esAdmin && sesion && (
          <button
            type="button"
            onClick={() => navigate('/dashboard', { state: { sesion_id: id } })}
            className="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium"
            style={{ borderColor: '#4B52E8', color: '#4B52E8' }}
          >
            <Pencil size={15} /> {t('detalle.editarPanel')}
          </button>
        )}
      </div>

      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>
          {sesion?.nombre_cliente ?? t('detalle.titulo')}
        </h1>
        {sesion && (
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {sesion.fecha} · {t('detalle.tipoCambio')}: {sesion.tipo_cambio_usd}
          </p>
        )}
      </div>

      {cargando ? (
        <p className="text-center" style={{ color: '#6B7280' }}>
          {t('detalle.cargando')}
        </p>
      ) : !sesion ? (
        <p className="text-center" style={{ color: '#6B7280' }}>
          {t('detalle.noEncontrada')}
        </p>
      ) : (
        <>
          {/* Totales */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <MetricCard titulo={t('historial.items')} valor={items.length} icono={<Package size={20} />} color="#4B52E8" />
            <MetricCard titulo={t('historial.totalRmb')} valor={`¥ ${fmt(totales.totalRmb)}`} icono={<Coins size={20} />} color="#F59E0B" />
            <MetricCard titulo={t('historial.totalUsd')} valor={`$ ${fmt(totales.totalUsd)}`} icono={<DollarSign size={20} />} color="#10B981" />
            <MetricCard titulo={t('historial.proveedores')} valor={totales.proveedores} icono={<Store size={20} />} color="#0D0D0D" />
          </div>

          {/* Descargar la cotización (PDF / Excel) — para Marcela y la contadora */}
          {items.length > 0 && (
            <section className="card flex flex-col gap-3">
              <h2 style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>{t('detalle.descargarTitulo')}</h2>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm" style={{ color: '#6B7280' }}>{t('detalle.idioma')}:</span>
                {IDIOMAS.map((op) => (
                  <button
                    key={op.code}
                    type="button"
                    onClick={() => setIdioma(op.code)}
                    className="rounded-lg border px-3 py-1.5 text-sm font-medium"
                    style={
                      idioma === op.code
                        ? { borderColor: '#4B52E8', backgroundColor: '#EEF0FD', color: '#4B52E8' }
                        : { borderColor: '#E5E7EB', color: '#6B7280' }
                    }
                  >
                    {op.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => descargar('pdf')}
                  disabled={generando !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: '#4B52E8', fontSize: 16, padding: '0 20px' }}
                >
                  <FileText size={18} /> {generando === 'pdf' ? t('detalle.generando') : t('detalle.descargarPdf')}
                </button>
                <button
                  type="button"
                  onClick={() => descargar('excel')}
                  disabled={generando !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: '#10B981', fontSize: 16, padding: '0 20px' }}
                >
                  <FileSpreadsheet size={18} /> {generando === 'excel' ? t('detalle.generando') : t('detalle.descargarExcel')}
                </button>
              </div>
            </section>
          )}

          {/* Ficha del cliente (solo lectura) */}
          {cliente && (
            <section className="card">
              <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
                {t('detalle.cliente')}
              </h2>
              <div className="grid gap-2 text-sm sm:grid-cols-2" style={{ color: '#374151' }}>
                <p className="flex items-center gap-2">
                  <Building2 size={15} style={{ color: '#9CA3AF' }} />
                  <strong>{cliente.nombre}</strong>
                  {cliente.empresa ? ` · ${cliente.empresa}` : ''}
                </p>
                {cliente.email && (
                  <p className="flex items-center gap-2">
                    <Mail size={15} style={{ color: '#9CA3AF' }} /> {cliente.email}
                  </p>
                )}
                {cliente.telefono && (
                  <p className="flex items-center gap-2">
                    <Phone size={15} style={{ color: '#9CA3AF' }} /> {cliente.telefono}
                  </p>
                )}
                {cliente.pais && <p className="flex items-center gap-2">📍 {cliente.pais}</p>}
              </div>
            </section>
          )}

          {/* Productos (solo lectura) */}
          <section className="card overflow-x-auto p-0">
            <h2 className="px-4 pt-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
              {t('detalle.productos')}
            </h2>
            {items.length === 0 ? (
              <p className="px-4 py-6 text-center" style={{ color: '#6B7280' }}>
                {t('detalle.sinProductos')}
              </p>
            ) : (
              <table className="mt-3 w-full text-sm">
                <thead style={{ backgroundColor: '#0D0D0D', color: '#FFFFFF' }}>
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">{t('detalle.descripcion')}</th>
                    <th className="px-4 py-3 text-left font-semibold">{t('detalle.proveedor')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('detalle.ctns')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('detalle.precioRmb')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('historial.totalRmb')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('historial.totalUsd')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => (
                    <tr key={item.id} style={{ backgroundColor: i % 2 === 0 ? '#FFFFFF' : '#F9F9F7' }}>
                      <td className="px-4 py-3 font-medium">
                        {item.descripcion_es || item.descripcion_en || item.item_no || '—'}
                      </td>
                      <td className="px-4 py-3">{item.supplier_nombre || '—'}</td>
                      <td className="px-4 py-3 text-right">{item.ctns}</td>
                      <td className="px-4 py-3 text-right">{item.price_rmb.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">{item.total_rmb.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">{item.total_usd.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          {/* Estado del envío / tracking (solo lectura, con la evidencia por etapa) */}
          <section className="card">
            <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
              {t('detalle.envio')}
            </h2>
            {seguimiento ? (
              <SeguimientoTimeline seguimiento={seguimiento} />
            ) : (
              <p className="text-sm" style={{ color: '#6B7280' }}>
                {t('detalle.sinEnvio')}
              </p>
            )}
          </section>
        </>
      )}
    </div>
  )
}

export default CotizacionDetalle
