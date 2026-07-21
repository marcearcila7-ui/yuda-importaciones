import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Wallet } from 'lucide-react'
import PortalLayout from '../../components/portal/PortalLayout'
import MetricCard from '../../components/MetricCard'
import { getMiCuenta } from '../../api/portal'
import type { EstadoCuenta } from '../../types/cuenta'

function PortalCuenta() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [cuenta, setCuenta] = useState<EstadoCuenta | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    getMiCuenta().then(setCuenta).catch(() => setError(true))
  }, [])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const fmtMon = (n: number, moneda: string) => `${moneda} ${fmt(n)}`

  return (
    <PortalLayout>
      <button
        type="button"
        onClick={() => navigate('/portal')}
        className="mb-3 flex items-center gap-1 text-sm font-medium"
        style={{ color: 'var(--yuda-text-secondary)' }}
      >
        <ArrowLeft size={16} /> {t('portal.volverCotizaciones')}
      </button>

      <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>{t('portal.miCuenta')}</h1>
      <p className="mb-5 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('portal.cuentaSubtitulo')}</p>

      {error ? (
        <div className="card"><p className="text-sm">{t('cuenta.errorCargar')}</p></div>
      ) : !cuenta ? (
        <div className="card"><p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('detalle.cargando')}</p></div>
      ) : (
        <div className="flex flex-col gap-5">
          {cuenta.totales_por_moneda.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
              {cuenta.totales_por_moneda.map((tm) => (
                <MetricCard key={tm.moneda} titulo={`${t('cuenta.saldoPendiente')} · ${tm.moneda}`} valor={fmtMon(tm.saldo_pendiente, tm.moneda)} icono={<Wallet size={20} />} color="var(--yuda-accent)" />
              ))}
            </div>
          )}

          {cuenta.pedidos.length === 0 ? (
            <section className="card">
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('portal.sinMovimientos')}</p>
            </section>
          ) : (
            cuenta.pedidos.map((p) => (
              <section key={p.sesion_id ?? 'sin'} className="card flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
                    {p.sesion_id ? (p.pedido_numero ?? '') : t('cuenta.sinPedido')}
                    <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}>{p.moneda}</span>
                  </h2>
                  <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {t('cuenta.saldoPendiente')}: <strong style={{ color: 'var(--yuda-accent)' }}>{fmtMon(p.saldo_pendiente, p.moneda)}</strong>
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}>
                        <th className="px-3 py-2 text-left font-semibold">{t('cuenta.envio')}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t('cuenta.fecha')}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t('cuenta.descripcion')}</th>
                        <th className="px-3 py-2 text-right font-semibold">{t('cuenta.valor')}</th>
                        <th className="px-3 py-2 text-right font-semibold">{t('cuenta.comisionCol')}</th>
                        <th className="px-3 py-2 text-right font-semibold">{t('cuenta.abono')}</th>
                        <th className="px-3 py-2 text-right font-semibold">{t('cuenta.saldo')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.movimientos.map((m, i) => (
                        <tr key={m.id} style={{ background: i % 2 ? 'var(--yuda-bg)' : 'transparent', borderBottom: '1px solid var(--yuda-border)' }}>
                          <td className="px-3 py-2">{m.envio ?? ''}</td>
                          <td className="px-3 py-2">{m.fecha ?? ''}</td>
                          <td className="px-3 py-2">{m.descripcion ?? ''}</td>
                          <td className="px-3 py-2 text-right">{fmt(m.valor_mercancia)}</td>
                          <td className="px-3 py-2 text-right">{fmt(m.comision_yuda)}</td>
                          <td className="px-3 py-2 text-right">{fmt(m.abono)}</td>
                          <td className="px-3 py-2 text-right font-semibold">{fmt(m.saldo)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            ))
          )}
        </div>
      )}
    </PortalLayout>
  )
}

export default PortalCuenta
