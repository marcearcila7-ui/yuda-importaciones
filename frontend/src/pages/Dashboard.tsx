import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import { Coins, DollarSign, Download, FileText, Package, ShoppingBag, Store } from 'lucide-react'
import CargaMasiva from '../components/CargaMasiva/CargaMasiva'
import ExportarCotizacion from '../components/ExportarCotizacion/ExportarCotizacion'
import GenerarPedidos from '../components/GenerarPedidos/GenerarPedidos'
import MetricCard from '../components/MetricCard'
import OCRUploader from '../components/OCRUploader/OCRUploader'
import PackingListTable from '../components/PackingListTable/PackingListTable'
import SesionSelector from '../components/SesionSelector/SesionSelector'
import { exportarPackingExcel } from '../api/packing'
import { getMetricas } from '../api/admin'
import { useAuthStore } from '../store/authStore'
import { usePackingStore } from '../store/packingStore'
import type { MetricasDashboard } from '../types/admin'
import type { OCRResultado } from '../types/ocr'
import type { ItemCreate } from '../types/packing'

// Mapea el idioma de i18n a un locale para fechas
const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

// Encabezado de página reutilizable
function PageHeader({ titulo, accesorio }: { titulo: string; accesorio?: ReactNode }) {
  const { i18n } = useTranslation()
  const hoy = new Date()
  const fecha = hoy.toLocaleDateString(LOCALES[i18n.language] || 'es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
  const fechaCap = fecha.charAt(0).toUpperCase() + fecha.slice(1)
  return (
    <div className="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>{titulo}</h1>
        {/* La fecha en mobile se muestra en el saludo personalizado */}
        <p className="hidden text-sm sm:block" style={{ color: '#6B7280' }}>
          {fechaCap}
        </p>
      </div>
      {accesorio}
    </div>
  )
}

// Card de sección con título
function SectionCard({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="card">
      <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: '#0D0D0D' }}>
        {titulo}
      </h2>
      {children}
    </section>
  )
}

function Dashboard() {
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const { usuario } = useAuthStore()
  const {
    sesionActual,
    items,
    sesiones,
    agregarItem,
    cargarItems,
    seleccionarSesion,
    cargarSesiones,
  } = usePackingStore()
  const [metricas, setMetricas] = useState<MetricasDashboard | null>(null)

  const esGestion = usuario?.rol === 'admin' || usuario?.rol === 'contadora'

  // Carga las métricas del mes (solo admin y contadora)
  useEffect(() => {
    if (!esGestion) return
    getMetricas()
      .then(setMetricas)
      .catch(() => setMetricas(null))
  }, [esGestion])

  // Si se llega desde el Historial con un sesion_id en el state, preseleccionar la sesión
  useEffect(() => {
    const sesionId = (location.state as { sesion_id?: string } | null)?.sesion_id
    if (!sesionId) return
    const preseleccionar = async () => {
      let sesion = sesiones.find((s) => s.id === sesionId)
      if (!sesion) {
        await cargarSesiones()
        sesion = usePackingStore.getState().sesiones.find((s) => s.id === sesionId)
      }
      if (sesion) await seleccionarSesion(sesion)
    }
    preseleccionar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state?.sesion_id])

  // Toma los datos confirmados del OCR y los agrega como producto de la cotización
  const handleItemConfirmado = async (datos: OCRResultado & { foto_url: string }) => {
    const itemCreate: ItemCreate = {
      supplier_nombre: datos.supplier_nombre ?? undefined,
      supplier_numero: datos.supplier_numero ?? undefined,
      foto_url: datos.foto_url,
      descripcion_zh: datos.descripcion_zh ?? undefined,
      qty_por_ctn: datos.qty_por_ctn ?? 1,
      price_rmb: datos.price_rmb ?? 0,
      gw: datos.gw ?? 0,
      largo_cm: datos.largo_cm ?? 0,
      ancho_cm: datos.ancho_cm ?? 0,
      alto_cm: datos.alto_cm ?? 0,
      ctns: 1,
    }
    await agregarItem(itemCreate)
    toast.success(t('ocr.exitoAgregado'))
  }

  // Descarga el Excel de la cotización
  const handleExportar = async () => {
    if (!sesionActual) return
    // En iPhone/Safari la pestaña debe abrirse DENTRO del toque (antes del await),
    // si no el navegador la bloquea o saca de la app.
    const ventana = window.open('', '_blank')
    try {
      const blob = await exportarPackingExcel(sesionActual.id)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        // Fallback (si el navegador bloqueó la pestaña): descarga directa
        const enlace = document.createElement('a')
        enlace.href = url
        enlace.download = `PackingList_${sesionActual.nombre_cliente}.xlsx`
        enlace.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
      toast.success(t('dashboard.listaDescargada'))
    } catch {
      ventana?.close()
      toast.error(t('dashboard.errorDescargar'))
    }
  }

  const fmt = (n: number) => n.toLocaleString('es-ES')

  // Fecha actual localizada (para el saludo mobile)
  const saludoFecha = (() => {
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
      <PageHeader
        titulo={t('dashboard.titulo')}
        accesorio={
          sesionActual ? (
            <span
              className="rounded-full px-4 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: '#4B52E8' }}
            >
              {sesionActual.nombre_cliente}
            </span>
          ) : undefined
        }
      />

      {/* Saludo personalizado: solo mobile */}
      {usuario && (
        <div className="sm:hidden">
          <h2 style={{ fontWeight: 700, fontSize: 20, color: '#0D0D0D' }}>
            {t('dashboard.saludo', { nombre: usuario.nombre })}
          </h2>
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {saludoFecha}
          </p>
        </div>
      )}

      {/* Métricas del mes (admin y contadora) */}
      {esGestion && metricas && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
          <MetricCard titulo={t('metricas.cotizacionesMes')} valor={metricas.total_sesiones_mes} icono={<ShoppingBag size={20} />} color="#4B52E8" />
          <MetricCard titulo={t('metricas.totalYuan')} valor={`¥ ${fmt(metricas.total_rmb_mes)}`} icono={<Coins size={20} />} color="#F59E0B" />
          <MetricCard titulo={t('metricas.totalUSD')} valor={`$ ${fmt(metricas.total_usd_mes)}`} icono={<DollarSign size={20} />} color="#10B981" />
          <MetricCard titulo={t('metricas.itemsProcesados')} valor={metricas.total_items_mes} icono={<Package size={20} />} color="#4B52E8" />
          <MetricCard titulo={t('metricas.proveedoresUnicos')} valor={metricas.proveedores_unicos_mes} icono={<Store size={20} />} color="#0D0D0D" />
          <MetricCard titulo={t('metricas.pedidosGenerados')} valor={metricas.total_pedidos_mes} icono={<FileText size={20} />} color="#4B52E8" />
        </div>
      )}

      {/* Crear / abrir cotización */}
      <SesionSelector />

      {/* Cotización activa */}
      {sesionActual && (
        <>
          <SectionCard titulo={t('dashboard.subirFoto')}>
            <OCRUploader onItemConfirmado={handleItemConfirmado} />
          </SectionCard>

          <SectionCard titulo={t('lote.titulo')}>
            <CargaMasiva />
          </SectionCard>

          <SectionCard titulo={t('dashboard.productos')}>
            <div className="mb-4 flex justify-end">
              <button
                type="button"
                onClick={handleExportar}
                className="flex items-center gap-2 font-semibold text-white"
                style={{ minHeight: 48, backgroundColor: '#10B981', borderRadius: 8, padding: '0 20px' }}
              >
                <Download size={18} /> {t('dashboard.exportarPacking')}
              </button>
            </div>
            <PackingListTable
              items={items}
              sesion_id={sesionActual.id}
              tipo_cambio_usd={sesionActual.tipo_cambio_usd}
              onItemActualizado={cargarItems}
            />
          </SectionCard>

          <ExportarCotizacion
            sesion_id={sesionActual.id}
            nombre_cliente={sesionActual.nombre_cliente}
          />

          <SectionCard titulo={t('dashboard.generarPedidos')}>
            <GenerarPedidos
              sesion_id={sesionActual.id}
              nombre_cliente={sesionActual.nombre_cliente}
            />
          </SectionCard>
        </>
      )}
    </div>
  )
}

export default Dashboard
