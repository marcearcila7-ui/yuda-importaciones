import { useTranslation } from 'react-i18next'
import { AlertCircle, DollarSign, FileText, Package, Ship } from 'lucide-react'
import MetricCard from '../MetricCard'
import type { PanelVentas } from '../../types/ventas'

export const fmtUSD = (n: number): string =>
  '$ ' + n.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function TarjetasVentas({ data }: { data: PanelVentas }) {
  const { t } = useTranslation()
  const sinMonto = data.contenedores_sin_monto ?? 0
  return (
    <>
    {sinMonto > 0 && (
      <p
        className="flex items-start gap-2 rounded-lg px-3 py-2 text-sm"
        style={{ backgroundColor: '#FFFBEB', color: '#92400E' }}
      >
        <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
        {t('ventas.sinMonto', { n: sinMonto })}
      </p>
    )}
    <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
      <MetricCard
        titulo={t('ventas.tarjetas.ventas')}
        valor={fmtUSD(data.ventas_total)}
        subtitulo={t('ventas.tarjetas.ventasSub')}
        icono={<DollarSign size={20} />}
        color="var(--yuda-success)"
      />
      <MetricCard
        titulo={t('ventas.tarjetas.enTransito')}
        valor={data.pedidos_en_transito}
        subtitulo={t('ventas.tarjetas.enTransitoSub')}
        icono={<Ship size={20} />}
        color="var(--yuda-primary)"
      />
      <MetricCard
        titulo={t('ventas.tarjetas.cotizaciones')}
        valor={data.cotizaciones_hechas}
        subtitulo={t('ventas.tarjetas.cotizacionesSub')}
        icono={<FileText size={20} />}
        color="var(--yuda-warning)"
      />
      <MetricCard
        titulo={t('ventas.tarjetas.contenedores')}
        valor={data.contenedores_total}
        subtitulo={t('ventas.tarjetas.contenedoresSub', { n: data.contenedores_vendedoras })}
        icono={<Package size={20} />}
        color="var(--yuda-accent)"
      />
    </div>
    </>
  )
}

export default TarjetasVentas
