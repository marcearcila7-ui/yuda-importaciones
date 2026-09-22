import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { getMetricasVendedoras } from '../api/admin'
import type { MetricaVendedora } from '../types/admin'

// Primer y último día del mes actual, en formato YYYY-MM-DD (lo que espera el
// filtro de fechas del Historial) -las métricas de esta tabla son del mes en
// curso, así que al entrar al detalle debe verse ese mismo recorte.
function rangoMesActual(): { desde: string; hasta: string } {
  const hoy = new Date()
  const desde = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
  const hasta = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { desde: fmt(desde), hasta: fmt(hasta) }
}

// Tabla de métricas del mes desglosadas por vendedora (solo la ve Marcela / admin)
function MetricasVendedoras() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [filas, setFilas] = useState<MetricaVendedora[] | null>(null)

  useEffect(() => {
    getMetricasVendedoras()
      .then((r) => setFilas(r.vendedoras))
      .catch(() => setFilas([]))
  }, [])

  if (filas === null) return null

  // Ceros para todas: es ruido, no información. Solo importa a quién
  // atender esta pantalla si tuvo actividad este mes.
  const conActividad = filas.filter((f) => f.total_sesiones > 0 || f.total_items > 0)

  const fmt = (n: number) => n.toLocaleString('es-ES')
  const totalCotizaciones = conActividad.reduce((a, f) => a + f.total_sesiones, 0)
  const totalItems = conActividad.reduce((a, f) => a + f.total_items, 0)
  const totalRmb = conActividad.reduce((a, f) => a + f.total_rmb, 0)
  const totalUsd = conActividad.reduce((a, f) => a + f.total_usd, 0)

  return (
    <section className="card">
      <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
        {t('metricas.porVendedora')}
      </h2>

      {conActividad.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('metricas.sinVendedoras')}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: 'var(--yuda-text-secondary)' }}>
                <th className="px-3 py-2 text-left font-semibold">{t('metricas.vendedora')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('metricas.cotizaciones')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('historial.items')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('historial.totalRmb')}</th>
                <th className="px-3 py-2 text-right font-semibold">{t('historial.totalUsd')}</th>
              </tr>
            </thead>
            <tbody>
              {conActividad.map((f) => (
                <tr
                  key={f.user_id}
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    const { desde, hasta } = rangoMesActual()
                    navigate('/historial', {
                      state: { fecha_desde: desde, fecha_hasta: hasta, vendedora_id: f.user_id, vendedora_nombre: f.nombre },
                    })
                  }}
                  onKeyDown={(e) => {
                    if (e.key !== 'Enter') return
                    const { desde, hasta } = rangoMesActual()
                    navigate('/historial', {
                      state: { fecha_desde: desde, fecha_hasta: hasta, vendedora_id: f.user_id, vendedora_nombre: f.nombre },
                    })
                  }}
                  className="cursor-pointer"
                  style={{ borderTop: '1px solid var(--yuda-primary-soft)' }}
                  title={t('metricas.verCotizacionesDe', { nombre: f.nombre })}
                >
                  <td className="px-3 py-2 font-medium" style={{ color: 'var(--yuda-accent)' }}>{f.nombre}</td>
                  <td className="px-3 py-2 text-right" style={{ color: 'var(--yuda-accent)' }}>{f.total_sesiones}</td>
                  <td className="px-3 py-2 text-right" style={{ color: 'var(--yuda-accent)' }}>{f.total_items}</td>
                  <td className="px-3 py-2 text-right" style={{ color: 'var(--yuda-accent)' }}>¥ {fmt(f.total_rmb)}</td>
                  <td className="px-3 py-2 text-right" style={{ color: 'var(--yuda-accent)' }}>$ {fmt(f.total_usd)}</td>
                </tr>
              ))}
              <tr style={{ borderTop: '2px solid var(--yuda-primary)' }}>
                <td className="px-3 py-2 font-bold" style={{ color: 'var(--yuda-primary)' }}>{t('metricas.totalGeneral')}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: 'var(--yuda-primary)' }}>{totalCotizaciones}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: 'var(--yuda-primary)' }}>{totalItems}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: 'var(--yuda-primary)' }}>¥ {fmt(totalRmb)}</td>
                <td className="px-3 py-2 text-right font-bold" style={{ color: 'var(--yuda-primary)' }}>$ {fmt(totalUsd)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default MetricasVendedoras
