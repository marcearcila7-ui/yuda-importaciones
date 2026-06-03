import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
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

// Encabezado de página reutilizable
function PageHeader({ titulo, accesorio }: { titulo: string; accesorio?: ReactNode }) {
  const hoy = new Date()
  const fecha = hoy.toLocaleDateString('es-ES', {
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
        <p className="text-sm" style={{ color: '#6B7280' }}>
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
    toast.success('Producto agregado a la cotización')
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
      toast.success('Lista descargada')
    } catch {
      ventana?.close()
      toast.error('No se pudo descargar la lista')
    }
  }

  const fmt = (n: number) => n.toLocaleString('es-ES')

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        titulo="Cotización"
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

      {/* Métricas del mes (admin y contadora) */}
      {esGestion && metricas && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard titulo="Cotizaciones este mes" valor={metricas.total_sesiones_mes} icono="📦" color="#4B52E8" />
          <MetricCard titulo="Total Yuan este mes" valor={`¥ ${fmt(metricas.total_rmb_mes)}`} icono="¥" color="#F59E0B" />
          <MetricCard titulo="Total USD este mes" valor={`$ ${fmt(metricas.total_usd_mes)}`} icono="💵" color="#10B981" />
          <MetricCard titulo="Ítems procesados" valor={metricas.total_items_mes} icono="📋" color="#4B52E8" />
          <MetricCard titulo="Proveedores únicos" valor={metricas.proveedores_unicos_mes} icono="🏭" color="#0D0D0D" />
          <MetricCard titulo="Pedidos generados" valor={metricas.total_pedidos_mes} icono="📄" color="#4B52E8" />
        </div>
      )}

      {/* Crear / abrir cotización */}
      <SesionSelector />

      {/* Cotización activa */}
      {sesionActual && (
        <>
          <SectionCard titulo="Subir foto de etiqueta">
            <OCRUploader onItemConfirmado={handleItemConfirmado} />
          </SectionCard>

          <SectionCard titulo="Productos de la cotización">
            <div className="mb-4 flex justify-end">
              <button
                type="button"
                onClick={handleExportar}
                className="font-semibold text-white"
                style={{ minHeight: 48, backgroundColor: '#10B981', borderRadius: 8, padding: '0 20px' }}
              >
                ⬇ Descargar lista (Excel)
              </button>
            </div>
            <PackingListTable
              items={items}
              sesion_id={sesionActual.id}
              tipo_cambio_usd={sesionActual.tipo_cambio_usd}
              onItemActualizado={cargarItems}
            />
          </SectionCard>

          <SectionCard titulo="Generar pedidos">
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
