import { useTranslation } from 'react-i18next'
import { DollarSign, FileText, Package, Ship } from 'lucide-react'
import MetricCard from '../MetricCard'
import type { PanelVentas } from '../../types/ventas'

export const fmtUSD = (n: number): string =>
  '$ ' + n.toLocaleString('es-CO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function TarjetasVentas({ data }: { data: PanelVentas }) {
  const { t } = useTranslation()
  return (
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
  )
}

export default TarjetasVentas
