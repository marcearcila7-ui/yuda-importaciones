import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, Coins, DollarSign, HandCoins, Wallet } from 'lucide-react'
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
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <MetricCard titulo={t('cuenta.compras')} valor={`$ ${fmt(cuenta.compras_totales)}`} icono={<DollarSign size={20} />} color="var(--yuda-primary)" />
            <MetricCard titulo={t('cuenta.comision')} valor={`$ ${fmt(cuenta.comision_total)}`} icono={<Coins size={20} />} color="var(--yuda-warning)" />
            <MetricCard titulo={t('cuenta.abonos')} valor={`$ ${fmt(cuenta.abonos_totales)}`} icono={<HandCoins size={20} />} color="var(--yuda-success)" />
            <MetricCard titulo={t('cuenta.saldoPendiente')} valor={`$ ${fmt(cuenta.saldo_pendiente)}`} icono={<Wallet size={20} />} color="var(--yuda-accent)" />
          </div>

          <section className="card flex flex-col gap-3">
            <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('cuenta.movimientos')}</h2>
            {cuenta.movimientos.length === 0 ? (
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('portal.sinMovimientos')}</p>
            ) : (
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
                    {cuenta.movimientos.map((m, i) => (
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
            )}
          </section>
        </div>
      )}
    </PortalLayout>
  )
}

export default PortalCuenta
