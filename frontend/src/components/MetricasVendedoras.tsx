import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getMetricasVendedoras } from '../api/admin'
import type { MetricaVendedora } from '../types/admin'

// Tabla de métricas del mes desglosadas por vendedora (solo la ve Marcela / admin)
function MetricasVendedoras() {
  const { t } = useTranslation()
  const [filas, setFilas] = useState<MetricaVendedora[] | null>(null)

  useEffect(() => {
    getMetricasVendedoras()
      .then((r) => setFilas(r.vendedoras))
      .catch(() => setFilas([]))
  }, [])

  if (filas === null) return null

  const fmt = (n: number) => n.toLocaleString('es-ES')
  const totalCotizaciones = filas.reduce((a, f) => a + f.total_sesiones, 0)
  const totalItems = filas.reduce((a, f) => a + f.total_items, 0)
  const totalRmb = filas.reduce((a, f) => a + f.total_rmb, 0)
  const totalUsd = filas.reduce((a, f) => a + f.total_usd, 0)

  return (
    <section className="card">
      <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
        {t('metricas.porVendedora')}
      </h2>

      {filas.length === 0 ? (
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {t('metricas.sinVendedoras')}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: '#6B7280' }}>
                <th className="px-3 py-2 text-left font-semibold">{t('metricas.vendedora')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('metricas.cotizaciones')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('historial.items')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('historial.totalRmb')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('historial.totalUsd')}</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f) => (
                <tr key={f.user_id} style={{ borderTop: '1px solid #EEF0FD' }}>
                  <td className="px-3 py-2 font-medium" style={{ color: '#0D0D0D' }}>{f.nombre}</td>
                  <td className="px-3 py-2 text-right" style={{ color: '#0D0D0D' }}>{f.total_sesiones}</td>
                  <td className="px-3 py-2 text-right" style={{ color: '#0D0D0D' }}>{f.total_items}</td>
                  <td className="px-3 py-2 text-right" style={{ color: '#0D0D0D' }}>¥ {fmt(f.total_rmb)}</td>
                  <td className="px-3 py-2 text-right" style={{ color: '#0D0D0D' }}>$ {fmt(f.total_usd)}</td>
                </tr>
              ))}
              <tr style={{ borderTop: '2px solid #4B52E8' }}>
                <td className="px-3 py-2 font-bold" style={{ color: '#4B52E8' }}>{t('metricas.totalGeneral')}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: '#4B52E8' }}>{totalCotizaciones}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: '#4B52E8' }}>{totalItems}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: '#4B52E8' }}>¥ {fmt(totalRmb)}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: '#4B52E8' }}>$ {fmt(totalUsd)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default MetricasVendedoras
