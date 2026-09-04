import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useTranslation } from 'react-i18next'
import axios from 'axios'
import { ArrowLeft, ArrowRight, Check, Coins, DollarSign, Download, FileText, Images, Package, ShoppingBag, Store, Trash2, X } from 'lucide-react'
import CargaMasiva from '../components/CargaMasiva/CargaMasiva'
import AdvertenciaFotos from '../components/AdvertenciaFotos/AdvertenciaFotos'
import BarraPasos from '../components/BarraPasos/BarraPasos'
import ClienteEnvio from '../components/ClienteEnvio/ClienteEnvio'
import ExportarCotizacion from '../components/ExportarCotizacion/ExportarCotizacion'
import GenerarPedidos from '../components/GenerarPedidos/GenerarPedidos'
import MetricCard from '../components/MetricCard'
import MetricasVendedoras from '../components/MetricasVendedoras'
import PackingListTable from '../components/PackingListTable/PackingListTable'
import SesionSelector from '../components/SesionSelector/SesionSelector'
import { eliminarSesion, exportarPackingExcel, exportarPackingPDF } from '../api/packing'
import { confirmar } from '../store/confirmStore'
import { getMetricas } from '../api/admin'
import { useAuthStore } from '../store/authStore'
import PanelVentas from '../components/ventas/PanelVentas'
import { usePackingStore } from '../store/packingStore'
import type { MetricasDashboard } from '../types/admin'

// Las tres etapas de una cotizacion. Se muestran con la misma barra que la carga
// de fotos para que la secuencia se lea igual en toda la app.
const PASOS_COTIZACION = [
  'dashboard.pasoFotos',
  'dashboard.pasoProductos',
  'dashboard.pasoCliente',
  'dashboard.pasoPedidos',
] as const

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
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>{titulo}</h1>
        {/* La fecha en mobile se muestra en el saludo personalizado */}
        <p className="hidden text-sm sm:block" style={{ color: 'var(--yuda-text-secondary)' }}>
          {fechaCap}
        </p>
      </div>
      {accesorio}
    </div>
  )
}

// Card de sección con título. El `id` permite volver la vista a esta sección
// cuando el contenido de arriba cambia de alto (ver CargaMasiva).
function SectionCard({ titulo, children, id }: { titulo: string; children: ReactNode; id?: string }) {
  return (
    <section className="card" id={id}>
      <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
        {titulo}
      </h2>
      {children}
    </section>
  )
}

// Separador que agrupa secciones (ej. "Para el cliente", "Documentos internos")
function GroupHeading({ texto }: { texto: string }) {
  return (
    <div className="mt-2 flex items-center gap-3">
      <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: 'var(--yuda-text-secondary)' }}>
        {texto.toUpperCase()}
      </span>
      <span className="h-px flex-1" style={{ backgroundColor: 'var(--yuda-border)' }} />
    </div>
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
    cargarItems,
    seleccionarSesion,
    cargarSesiones,
    volverAlInicio,
  } = usePackingStore()
  const [metricas, setMetricas] = useState<MetricasDashboard | null>(null)
  // Pantalla del asistente de cotización en la que está parada la vendedora.
  // Cada paso es una pantalla propia: se avanza y se vuelve, nunca se ve todo junto.
  const [pasoVista, setPasoVista] = useState(1)
  // Sesión para la que ya confirmaron la advertencia de fotos (se reinicia en cada
  // carga y al abrir otra cotización → la alerta vuelve a salir cada vez).
  const [confirmadoParaSesion, setConfirmadoParaSesion] = useState<string | null>(null)

  // Hasta que no hay productos, todo lo que viene despues (documento del cliente,
  // pedidos a proveedores, registros internos) es ruido: no se puede usar todavia
  // y llena la pantalla de botones que no llevan a ninguna parte.
  const hayProductos = items.length > 0

  // Las métricas (generales y por vendedora) solo las ve Marcela / admin
  const esAdmin = usuario?.rol === 'admin'
  // El bloque de cliente y envío lo gestionan admin y vendedoras
  const esStaffVentas = usuario?.rol === 'admin' || usuario?.rol === 'vendedora'

  // Al abrir otra cotización se empieza de nuevo por la primera pantalla.
  useEffect(() => {
    setPasoVista(1)
  }, [sesionActual?.id])

  // Si se quedó sin productos (los borró todos), las pantallas siguientes ya no
  // aplican: se la devuelve a la primera en vez de dejarla en una pantalla muerta.
  useEffect(() => {
    if (!hayProductos && pasoVista !== 1) setPasoVista(1)
  }, [hayProductos, pasoVista])

  // Cambiar de pantalla debe empezar arriba, no a media página.
  const irAPaso = (paso: number) => {
    setPasoVista(paso)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Carga las métricas del mes (solo admin)
  useEffect(() => {
    if (!esAdmin) return
    getMetricas()
      .then(setMetricas)
      .catch(() => setMetricas(null))
  }, [esAdmin])

  // Escritorio limpio para Marcela: al entrar a "Cotización" sin abrir una a
  // propósito (ej. desde el Historial), no arrastrar la cotización que estuviera
  // activa de antes.
  useEffect(() => {
    const sesionId = (location.state as { sesion_id?: string } | null)?.sesion_id
    if (esAdmin && !sesionId) volverAlInicio()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

  // Elimina la cotización abierta. Si ya se le había enviado al cliente,
  // también deja de verla en su portal.
  const eliminarCotizacion = async () => {
    if (!sesionActual) return
    const ok = await confirmar({
      mensaje: t('dashboard.confirmarEliminarCotizacion', { cliente: sesionActual.nombre_cliente }),
      peligro: true,
      textoConfirmar: t('dashboard.eliminarCotizacion'),
    })
    if (!ok) return
    try {
      await eliminarSesion(sesionActual.id)
      toast.success(t('dashboard.cotizacionEliminada'))
      volverAlInicio()
      await cargarSesiones()
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      toast.error(typeof detalle === 'string' ? detalle : t('dashboard.errorEliminarCotizacion'))
    }
  }

  // Descarga el Packing List interno (Excel o PDF)
  const descargarPacking = async (tipo: 'excel' | 'pdf') => {
    if (!sesionActual) return
    // En iPhone/Safari la pestaña debe abrirse DENTRO del toque (antes del await),
    // si no el navegador la bloquea o saca de la app.
    const ventana = window.open('', '_blank')
    try {
      const blob =
        tipo === 'excel'
          ? await exportarPackingExcel(sesionActual.id)
          : await exportarPackingPDF(sesionActual.id)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        // Fallback (si el navegador bloqueó la pestaña): descarga directa
        const enlace = document.createElement('a')
        enlace.href = url
        enlace.download = `PackingList_${sesionActual.nombre_cliente}.${tipo === 'excel' ? 'xlsx' : 'pdf'}`
        enlace.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
      toast.success(t('dashboard.listaDescargada'))
    } catch {
      ventana?.close()
      toast.error(t('dashboard.errorDescargar'))
    }
  }

  // La contadora no gestiona cotizaciones: su pantalla es el historial.
  // (red de seguridad si entra por URL directa o por el fallback de rutas).
  if (usuario?.rol === 'contadora') return <Navigate to="/historial" replace />

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
      {esAdmin && <PanelVentas />}
      <PageHeader
        titulo={t('dashboard.titulo')}
        accesorio={
          sesionActual ? (
            <span
              className="rounded-full px-4 py-2 text-sm font-semibold text-white"
              style={{ backgroundColor: 'var(--yuda-primary)' }}
            >
              {sesionActual.nombre_cliente}
            </span>
          ) : undefined
        }
      />

      {/* Saludo personalizado: solo mobile */}
      {usuario && (
        <div className="sm:hidden">
          <h2 style={{ fontWeight: 700, fontSize: 20, color: 'var(--yuda-accent)' }}>
            {t('dashboard.saludo', { nombre: usuario.nombre })}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {saludoFecha}
          </p>
        </div>
      )}

      {/* Métricas del mes (solo Marcela / admin) */}
      {esAdmin && metricas && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
          <MetricCard titulo={t('metricas.cotizacionesMes')} valor={metricas.total_sesiones_mes} icono={<ShoppingBag size={20} />} color="var(--yuda-primary)" />
          <MetricCard titulo={t('metricas.totalYuan')} valor={`¥ ${fmt(metricas.total_rmb_mes)}`} icono={<Coins size={20} />} color="var(--yuda-warning)" />
          <MetricCard titulo={t('metricas.totalUSD')} valor={`$ ${fmt(metricas.total_usd_mes)}`} icono={<DollarSign size={20} />} color="var(--yuda-success)" />
          <MetricCard titulo={t('metricas.itemsProcesados')} valor={metricas.total_items_mes} icono={<Package size={20} />} color="var(--yuda-primary)" />
          <MetricCard titulo={t('metricas.proveedoresUnicos')} valor={metricas.proveedores_unicos_mes} icono={<Store size={20} />} color="var(--yuda-accent)" />
          <MetricCard titulo={t('metricas.pedidosGenerados')} valor={metricas.total_pedidos_mes} icono={<FileText size={20} />} color="var(--yuda-primary)" />
        </div>
      )}

      {/* Métricas por vendedora (solo Marcela / admin) */}
      {esAdmin && <MetricasVendedoras />}

      {/* Crear / abrir cotización. Con una ya abierta desaparece: manda el asistente,
          y dejarlo arriba era volver a mostrar dos etapas en la misma pantalla. */}
      {esStaffVentas && !sesionActual && <SesionSelector />}

      {/* Cotización activa */}
      {sesionActual && (
        <>
          {/* Barra de la cotización abierta: cuál es + cerrarla */}
          <div
            className="flex flex-wrap items-center justify-between gap-2 rounded-xl px-4 py-3"
            style={{ backgroundColor: 'var(--yuda-primary-soft)' }}
          >
            <p className="text-sm" style={{ color: 'var(--yuda-primary)' }}>
              {t('dashboard.cotizacionAbierta')}{' '}
              <strong>{sesionActual.nombre_cliente}</strong>
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={volverAlInicio}
                className="flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm font-semibold"
                style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)', backgroundColor: 'var(--yuda-white)' }}
              >
                <X size={15} /> {t('dashboard.cerrarCotizacion')}
              </button>
              {/* Borrarla del todo (también sirve para los borradores que aún no
                  están vinculados a ningún cliente). */}
              <button
                type="button"
                onClick={eliminarCotizacion}
                className="flex items-center gap-1 rounded-lg border px-3 py-1.5 text-sm font-semibold"
                style={{ borderColor: 'var(--yuda-error)', color: 'var(--yuda-error)', backgroundColor: 'var(--yuda-white)' }}
              >
                <Trash2 size={15} /> {t('dashboard.eliminarCotizacion')}
              </button>
            </div>
          </div>

          <BarraPasos
            pasos={PASOS_COTIZACION}
            activo={pasoVista}
            maxAlcanzable={hayProductos ? PASOS_COTIZACION.length : 1}
            onIr={irAPaso}
          />

          {/* PANTALLA 1: solo las fotos. Nada mas: ni la tabla ni lo que viene despues. */}
          {pasoVista === 1 && (
            <SectionCard titulo={t('lote.titulo')} id="seccion-carga">
              <CargaMasiva onTerminado={() => irAPaso(2)} />
            </SectionCard>
          )}

          {/* PANTALLA 2: la lista de productos ya cargados */}
          {pasoVista === 2 && (
            <SectionCard titulo={t('dashboard.productos')} id="seccion-productos">
              <PackingListTable
                items={items}
                tipo_cambio_usd={sesionActual.tipo_cambio_usd}
                onItemActualizado={cargarItems}
              />
              <button
                type="button"
                onClick={() => irAPaso(1)}
                className="mt-4 flex items-center justify-center gap-2 font-semibold"
                style={{
                  minHeight: 48,
                  borderRadius: 8,
                  padding: '0 20px',
                  backgroundColor: 'var(--yuda-primary-soft)',
                  color: 'var(--yuda-primary)',
                }}
              >
                <Images size={18} /> {t('lote.agregarMas')}
              </button>
            </SectionCard>
          )}

          {/* PANTALLA 3: el documento del cliente y el envío a su portal */}
          {pasoVista === 3 && (
            <>
              <ExportarCotizacion
                sesion_id={sesionActual.id}
                nombre_cliente={sesionActual.nombre_cliente}
              />

              {esStaffVentas && (
                <SectionCard titulo={t('envio.titulo')}>
                  <ClienteEnvio
                    sesionId={sesionActual.id}
                    clienteIdInicial={sesionActual.cliente_id ?? null}
                    enviadaInicial={sesionActual.enviada_cliente ?? false}
                    nombreClienteSesion={sesionActual.nombre_cliente}
                  />
                </SectionCard>
              )}
            </>
          )}

          {/* PANTALLA 4: pedidos a proveedores y los registros internos */}
          {pasoVista === 4 && (
            <>
              <SectionCard titulo={t('dashboard.generarPedidos')}>
                <p className="mb-4 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('dashboard.generarPedidosAyuda')}
                </p>
                <GenerarPedidos
                  sesion_id={sesionActual.id}
                  nombre_cliente={sesionActual.nombre_cliente}
                  permitirCantidadesCliente={sesionActual.pedido_recibido_at != null}
                />
              </SectionCard>

              <GroupHeading texto={t('dashboard.grupoInterno')} />

              <SectionCard titulo={t('dashboard.exportarPackingTitulo')}>
                <p className="mb-4 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('dashboard.exportarPackingAyuda')}
                </p>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => descargarPacking('excel')}
                    className="flex items-center justify-center gap-2 font-semibold text-white"
                    style={{ minHeight: 48, backgroundColor: 'var(--yuda-success)', borderRadius: 8, padding: '0 20px' }}
                  >
                    <Download size={18} /> {t('dashboard.exportarPacking')}
                  </button>
                  <button
                    type="button"
                    onClick={() => descargarPacking('pdf')}
                    className="flex items-center justify-center gap-2 font-semibold text-white"
                    style={{ minHeight: 48, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 20px' }}
                  >
                    <FileText size={18} /> {t('dashboard.exportarPackingPdf')}
                  </button>
                </div>
              </SectionCard>
            </>
          )}

          {/* Avanzar y volver: siempre al pie de la pantalla, siempre en el mismo lugar */}
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={() => irAPaso(pasoVista - 1)}
              disabled={pasoVista === 1}
              className="flex items-center justify-center gap-2 font-semibold disabled:opacity-40"
              style={{
                minHeight: 48,
                borderRadius: 8,
                padding: '0 20px',
                border: '2px solid var(--yuda-border)',
                color: 'var(--yuda-text-secondary)',
                backgroundColor: 'var(--yuda-white)',
              }}
            >
              <ArrowLeft size={18} /> {t('dashboard.pasoAtras')}
            </button>

            <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
              {pasoVista === 1 && !hayProductos && (
                <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('dashboard.avisoSinProductosAvanzar')}
                </span>
              )}
              {pasoVista < PASOS_COTIZACION.length ? (
                <button
                  type="button"
                  onClick={() => irAPaso(pasoVista + 1)}
                  disabled={!hayProductos}
                  className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-40"
                  style={{ minHeight: 48, borderRadius: 8, padding: '0 20px', backgroundColor: 'var(--yuda-primary)' }}
                >
                  {t('dashboard.pasoSiguiente')} <ArrowRight size={18} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={volverAlInicio}
                  className="flex items-center justify-center gap-2 font-semibold text-white"
                  style={{ minHeight: 48, borderRadius: 8, padding: '0 20px', backgroundColor: 'var(--yuda-success)' }}
                >
                  <Check size={18} /> {t('dashboard.pasoTerminar')}
                </button>
              )}
            </div>
          </div>
        </>
      )}

      {/* Advertencia OBLIGATORIA sobre cómo tomar las fotos: aparece al abrir/iniciar
          una cotización y bloquea hasta que la vendedora confirma que sus fotos cumplen. */}
      {sesionActual && confirmadoParaSesion !== sesionActual.id && (
        <AdvertenciaFotos
          onConfirmar={() => setConfirmadoParaSesion(sesionActual.id)}
          onCancelar={volverAlInicio}
        />
      )}
    </div>
  )
}

export default Dashboard
