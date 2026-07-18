import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, Ship } from 'lucide-react'
import { getPanelVentas, getUsuarios } from '../api/admin'
import RangoFechas from '../components/ventas/RangoFechas'
import type { Rango } from '../components/ventas/RangoFechas'
import TarjetasVentas, { fmtUSD } from '../components/ventas/TarjetasVentas'
import { descargarCSV } from '../utils/csv'
import type { PanelVentas } from '../types/ventas'

const LOCALES: Record<string, string> = { es: 'es-CO', en: 'en-US', zh: 'zh-CN' }

function Ventas() {
  const { t, i18n } = useTranslation()
  const [rango, setRango] = useState<Rango>({})
  const [vendedoraId, setVendedoraId] = useState('')
  const [vendedoras, setVendedoras] = useState<{ id: string; nombre: string }[]>([])
  const [data, setData] = useState<PanelVentas | null>(null)
  const [cargando, setCargando] = useState(true)

  useEffect(() => {
    getUsuarios()
      .then((us) => setVendedoras(us.filter((u) => u.rol === 'vendedora').map((u) => ({ id: u.id, nombre: u.nombre }))))
      .catch(() => {})
  }, [])

  useEffect(() => {
    setCargando(true)
    getPanelVentas({ ...rango, vendedora_id: vendedoraId || undefined })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setCargando(false))
  }, [rango, vendedoraId])

  const fmtFechaHora = (iso: string | null): string => {
    if (!iso) return '—'
    const d = new Date(iso)
    return Number.isNaN(d.getTime())
      ? '—'
      : d.toLocaleString(LOCALES[i18n.language] ?? 'es-CO', { dateStyle: 'medium', timeStyle: 'short' })
  }
  const estadoLabel = (k: string): string => t(`seguimiento.estados.${k}`)

  const exportarVendedoras = () => {
    if (!data) return
    descargarCSV(
      `ventas_por_vendedora_${rango.desde ?? 'todo'}_${rango.hasta ?? ''}`,
      data.por_vendedora.map((v) => ({
        vendedora: v.nombre,
        cotizaciones: v.cotizaciones,
        contenedores: v.contenedores,
        ventas_usd: v.ventas,
      })),
      [
        { key: 'vendedora', label: t('ventas.tabla.vendedora') },
        { key: 'cotizaciones', label: t('ventas.tabla.cotizaciones') },
        { key: 'contenedores', label: t('ventas.tabla.contenedores') },
        { key: 'ventas_usd', label: t('ventas.tabla.ventasUsd') },
      ],
    )
  }

  const exportarDespachos = () => {
    if (!data) return
    descargarCSV(
      `ventas_despachos_${rango.desde ?? 'todo'}_${rango.hasta ?? ''}`,
      data.despachos.map((d) => ({
        numero: d.numero,
        cliente: d.cliente,
        vendedora: d.vendedora,
        estado: estadoLabel(d.estado),
        bl: d.bl_numero ?? '',
        naviera: d.naviera ?? '',
        monto_usd: d.monto_venta,
        despachado: d.despachado_at ? fmtFechaHora(d.despachado_at) : '',
        fecha_cotizacion: d.fecha_cotizacion,
      })),
      [
        { key: 'numero', label: t('ventas.tabla.numero') },
        { key: 'cliente', label: t('ventas.tabla.cliente') },
        { key: 'vendedora', label: t('ventas.tabla.vendedora') },
        { key: 'estado', label: t('ventas.tabla.estado') },
        { key: 'bl', label: t('ventas.tabla.bl') },
        { key: 'naviera', label: t('ventas.tabla.naviera') },
        { key: 'monto_usd', label: t('ventas.tabla.montoUsd') },
        { key: 'despachado', label: t('ventas.tabla.despachado') },
        { key: 'fecha_cotizacion', label: t('ventas.tabla.fechaCotizacion') },
      ],
    )
  }

  const btnCsv =
    'flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm font-medium'

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>💰 {t('ventas.titulo')}</h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('ventas.subtitulo')}</p>
      </div>

      {/* Filtros */}
      <div className="flex flex-col gap-3">
        <RangoFechas onChange={setRango} inicial="30" />
        <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          <span>{t('ventas.filtrarVendedora')}:</span>
          <select
            value={vendedoraId}
            onChange={(e) => setVendedoraId(e.target.value)}
            className="rounded-lg border border-gray-200 px-2 py-1.5 focus:border-[var(--yuda-primary)] focus:outline-none"
            style={{ fontSize: 16 }}
          >
            <option value="">{t('ventas.todasVendedoras')}</option>
            {vendedoras.map((v) => (
              <option key={v.id} value={v.id}>{v.nombre}</option>
            ))}
          </select>
        </div>
      </div>

      {!data ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {cargando ? t('ventas.cargando') : t('ventas.sinDatos')}
        </p>
      ) : (
        <>
          <TarjetasVentas data={data} />

          {/* Aporte de las vendedoras */}
          <div className="card flex flex-col gap-2">
            <p className="text-sm" style={{ color: 'var(--yuda-text)' }}>
              {t('ventas.contenedoresVendedoras', {
                v: data.contenedores_vendedoras,
                total: data.contenedores_total,
              })}{' '}
              · <strong>{fmtUSD(data.ventas_vendedoras)}</strong> {t('ventas.enVentas')}
            </p>
          </div>

          {/* Por vendedora */}
          <section className="card overflow-x-auto p-0">
            <div className="flex items-center justify-between px-4 pt-4">
              <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('ventas.porVendedora')}</h2>
              <button type="button" onClick={exportarVendedoras} className={btnCsv} style={{ borderColor: 'var(--yuda-success)', color: 'var(--yuda-success)' }}>
                <Download size={15} /> {t('ventas.exportarCsv')}
              </button>
            </div>
            <table className="mt-3 w-full min-w-[520px] text-sm">
              <thead style={{ backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' }}>
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.vendedora')}</th>
                  <th className="px-4 py-3 text-right font-semibold">{t('ventas.tabla.cotizaciones')}</th>
                  <th className="px-4 py-3 text-right font-semibold">{t('ventas.tabla.contenedores')}</th>
                  <th className="px-4 py-3 text-right font-semibold">{t('ventas.tabla.ventasUsd')}</th>
                </tr>
              </thead>
              <tbody>
                {data.por_vendedora.map((v, i) => (
                  <tr key={v.vendedora_id} style={{ backgroundColor: i % 2 === 0 ? 'var(--yuda-white)' : '#F9F9F7' }}>
                    <td className="px-4 py-3 font-medium">{v.nombre}</td>
                    <td className="px-4 py-3 text-right">{v.cotizaciones}</td>
                    <td className="px-4 py-3 text-right">{v.contenedores}</td>
                    <td className="px-4 py-3 text-right font-semibold">{fmtUSD(v.ventas)}</td>
                  </tr>
                ))}
                {data.por_vendedora.length === 0 && (
                  <tr><td colSpan={4} className="px-4 py-6 text-center" style={{ color: 'var(--yuda-text-secondary)' }}>{t('ventas.sinVendedoras')}</td></tr>
                )}
              </tbody>
            </table>
          </section>

          {/* Detalle de despachos */}
          <section className="card overflow-x-auto p-0">
            <div className="flex items-center justify-between px-4 pt-4">
              <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
                <Ship size={18} style={{ color: 'var(--yuda-primary)' }} /> {t('ventas.despachos')}
              </h2>
              <button type="button" onClick={exportarDespachos} className={btnCsv} style={{ borderColor: 'var(--yuda-success)', color: 'var(--yuda-success)' }}>
                <Download size={15} /> {t('ventas.exportarCsv')}
              </button>
            </div>
            <table className="mt-3 w-full min-w-[760px] text-sm">
              <thead style={{ backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' }}>
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.numero')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.cliente')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.vendedora')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.estado')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.bl')}</th>
                  <th className="px-4 py-3 text-right font-semibold">{t('ventas.tabla.montoUsd')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('ventas.tabla.despachado')}</th>
                </tr>
              </thead>
              <tbody>
                {data.despachos.map((d, i) => (
                  <tr key={d.sesion_id} style={{ backgroundColor: i % 2 === 0 ? 'var(--yuda-white)' : '#F9F9F7' }}>
                    <td className="px-4 py-3 font-medium">{d.numero}</td>
                    <td className="px-4 py-3">{d.cliente}</td>
                    <td className="px-4 py-3">{d.vendedora}</td>
                    <td className="px-4 py-3">{estadoLabel(d.estado)}</td>
                    <td className="px-4 py-3">{d.bl_numero ?? '—'}</td>
                    <td className="px-4 py-3 text-right font-semibold">{fmtUSD(d.monto_venta)}</td>
                    <td className="px-4 py-3" style={{ color: 'var(--yuda-text-secondary)' }}>{fmtFechaHora(d.despachado_at)}</td>
                  </tr>
                ))}
                {data.despachos.length === 0 && (
                  <tr><td colSpan={7} className="px-4 py-6 text-center" style={{ color: 'var(--yuda-text-secondary)' }}>{t('ventas.sinDespachos')}</td></tr>
                )}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}

export default Ventas
