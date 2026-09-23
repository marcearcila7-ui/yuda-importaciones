import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, ArrowLeft, Download, FileText, Wallet } from 'lucide-react'
import PortalLayout from '../../components/portal/PortalLayout'
import MetricCard from '../../components/MetricCard'
import { descargarMiCuentaPdfContable, getMiCuenta } from '../../api/portal'
import type { EstadoCuenta } from '../../types/cuenta'

function PortalCuenta() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [cuenta, setCuenta] = useState<EstadoCuenta | null>(null)
  const [error, setError] = useState(false)
  const [descargandoPdf, setDescargandoPdf] = useState(false)

  useEffect(() => {
    getMiCuenta().then(setCuenta).catch(() => setError(true))
  }, [])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  const fmtMon = (n: number, moneda: string) => `${moneda} ${fmt(n)}`

  const descargarPdfOficial = async () => {
    setDescargandoPdf(true)
    try {
      const blob = await descargarMiCuentaPdfContable()
      const url = URL.createObjectURL(blob)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = 'estado_cuenta.pdf'
      enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      toast.error(t('portal.errorDescargarPdfContable'))
    } finally {
      setDescargandoPdf(false)
    }
  }

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
          {cuenta.estado_cuenta_contable ? (
            <section className="card flex flex-col gap-3" style={{ borderColor: 'var(--yuda-primary)', borderWidth: 1 }}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
                  {t('portal.estadoCuentaOficialTitulo')}
                </h2>
                <button
                  type="button"
                  onClick={descargarPdfOficial}
                  disabled={descargandoPdf}
                  className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-primary)' }}
                >
                  <Download size={16} /> {descargandoPdf ? t('cuenta.descargando') : t('portal.descargarPdfContable')}
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <span style={{ fontWeight: 700, fontSize: 22, color: 'var(--yuda-accent)' }}>
                  {fmtMon(cuenta.estado_cuenta_contable.saldo_pendiente, cuenta.estado_cuenta_contable.moneda)}
                </span>
                <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {cuenta.estado_cuenta_contable.es_a_favor ? t('portal.saldoAFavor') : t('cuenta.saldoPendiente')}
                </span>
                {cuenta.estado_cuenta_contable.dias_vencido != null && !cuenta.estado_cuenta_contable.es_a_favor && (
                  <span
                    className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold"
                    style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}
                  >
                    <AlertTriangle size={12} /> {cuenta.estado_cuenta_contable.estado_atraso}
                  </span>
                )}
              </div>
              {cuenta.estado_cuenta_contable.pedidos.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm" style={{ borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}>
                        <th className="px-3 py-2 text-left font-semibold">{t('portal.pedido')}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t('cuenta.fecha')}</th>
                        <th className="px-3 py-2 text-right font-semibold">{t('cuenta.valor')}</th>
                        <th className="px-3 py-2 text-right font-semibold">{t('cuenta.saldo')}</th>
                        <th className="px-3 py-2 text-left font-semibold">{t('portal.estado')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cuenta.estado_cuenta_contable.pedidos.map((p, i) => (
                        <tr key={p.numero_pedido} style={{ background: i % 2 ? 'var(--yuda-bg)' : 'transparent', borderBottom: '1px solid var(--yuda-border)' }}>
                          <td className="px-3 py-2">{p.numero_pedido}</td>
                          <td className="px-3 py-2">{p.fecha_pedido ?? ''}</td>
                          <td className="px-3 py-2 text-right">{fmtMon(p.total, cuenta.estado_cuenta_contable!.moneda)}</td>
                          <td className="px-3 py-2 text-right font-semibold">{fmtMon(p.pendiente, cuenta.estado_cuenta_contable!.moneda)}</td>
                          <td className="px-3 py-2">{p.estado}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          ) : cuenta.estado_cuenta_oficial_url ? (
            <a
              href={cuenta.estado_cuenta_oficial_url}
              target="_blank"
              rel="noreferrer"
              className="card flex items-center gap-3"
              style={{ borderColor: 'var(--yuda-primary)', borderWidth: 1 }}
            >
              <div
                className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full"
                style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
              >
                <FileText size={20} />
              </div>
              <div>
                <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>
                  {t('portal.estadoCuentaOficialTitulo')}
                </p>
                <p className="text-sm" style={{ color: 'var(--yuda-primary)' }}>{t('portal.verDocumento')}</p>
              </div>
            </a>
          ) : null}

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
