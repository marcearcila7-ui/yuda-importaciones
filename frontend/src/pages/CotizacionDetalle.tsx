import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ArrowLeft, Building2, Coins, DollarSign, FileSpreadsheet, FileText, Mail, Package, Pencil, Phone, Printer, Receipt, Ship, Store } from 'lucide-react'
import CubicajePanel from '../components/CubicajePanel'
import GestionPedidoCliente from '../components/GestionPedidoCliente'
import MetricCard from '../components/MetricCard'
import PedidoCliente from '../components/PedidoCliente'
import SeguimientoEditor from '../components/SeguimientoEditor'
import SeguimientoTimeline from '../components/portal/SeguimientoTimeline'
import { exportarCotizacionExcel, exportarCotizacionPDF, exportarFacturaExcel, exportarFacturaPDF, getItems, getSesiones } from '../api/packing'
import { getContenedores } from '../api/contenedores'
import { getCliente, getSeguimiento } from '../api/clientes'
import { useAuthStore } from '../store/authStore'
import type { ItemResponse, Sesion } from '../types/packing'
import type { Contenedor } from '../types/contenedor'
import type { Cliente } from '../types/cliente'
import type { Seguimiento } from '../types/seguimiento'

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]


// Vista de solo lectura de una cotización para la contadora y el admin (desde el
// historial). Muestra los productos, los totales, la ficha del cliente y el
// estado del envío (tracking/BL, con la evidencia de cada etapa). Marcela puede
// descargar el PDF/Excel de la cotización desde aquí.
function CotizacionDetalle() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { t, i18n } = useTranslation()
  const rol = useAuthStore((s) => s.usuario?.rol)
  const esAdmin = rol === 'admin'
  const [sesion, setSesion] = useState<Sesion | null>(null)
  const [items, setItems] = useState<ItemResponse[]>([])
  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [seguimiento, setSeguimiento] = useState<Seguimiento | null>(null)
  const [cargando, setCargando] = useState(true)
  const [idioma, setIdioma] = useState<string>(['es', 'en', 'zh'].includes(i18n.language) ? i18n.language : 'es')
  const [generando, setGenerando] = useState<'pdf' | 'excel' | 'imprimir' | null>(null)
  // Generar el documento (con fotos incrustadas) tarda y no hay forma de medir
  // el avance real desde el navegador (una sola respuesta del servidor). Este
  // porcentaje avanza solo hacia un tope, igual que en la carga masiva: no
  // promete un tiempo exacto, pero deja claro que sigue en marcha.
  const [pct, setPct] = useState(0)
  useEffect(() => {
    setPct(0)
  }, [generando])
  useEffect(() => {
    if (!generando) return
    const iv = setInterval(() => setPct((v) => (v >= 95 ? v : v + (95 - v) * 0.08)), 200)
    return () => clearInterval(iv)
  }, [generando])
  const [contenedores, setContenedores] = useState<Contenedor[]>([])
  const [contenedorId, setContenedorId] = useState<string>('')
  const [generandoFactura, setGenerandoFactura] = useState<'pdf' | 'excel' | null>(null)
  const [pctFactura, setPctFactura] = useState(0)
  useEffect(() => {
    setPctFactura(0)
  }, [generandoFactura])
  useEffect(() => {
    if (!generandoFactura) return
    const iv = setInterval(() => setPctFactura((v) => (v >= 95 ? v : v + (95 - v) * 0.08)), 200)
    return () => clearInterval(iv)
  }, [generandoFactura])
  // De (FROM) y Para (TO) editables de la factura. Para se precarga con el cliente.
  const [facturaDe, setFacturaDe] = useState<string>('')
  const [facturaPara, setFacturaPara] = useState<string>('')
  // 4 pestañas: cada una responde una sola pregunta (qué se le cotizó al
  // cliente / qué hay que hacer con el pedido y bodega / en qué va el envío /
  // cubicaje), en vez de una sola pantalla larga con todo mezclado.
  // Gestión primero para quien puede actuar (admin/vendedora); la contadora no
  // gestiona pedidos, así que arranca directo en la cotización. Si se llegó
  // acá desde un aviso de la campanita, ese aviso ya dice a qué pestaña ir
  // (ej. un reporte de cubicaje abre directo en "Cubicaje").
  const tabDesdeAviso = (location.state as { tab?: string } | null)?.tab
  const [tab, setTab] = useState<'gestion' | 'cotizacion' | 'seguimiento' | 'cubicaje'>(
    (tabDesdeAviso as 'gestion' | 'cotizacion' | 'seguimiento' | 'cubicaje') ??
      (rol === 'admin' || rol === 'vendedora' ? 'gestion' : 'cotizacion'),
  )
  const [recargarTick, setRecargarTick] = useState(0)
  const recargar = () => setRecargarTick((n) => n + 1)

  useEffect(() => {
    let activo = true
    const cargar = async () => {
      setCargando(true)
      try {
        const [sesiones, itemsData, seg, conts] = await Promise.all([
          getSesiones(),
          getItems(id),
          getSeguimiento(id).catch(() => null),
          getContenedores().catch(() => [] as Contenedor[]),
        ])
        if (!activo) return
        const s = sesiones.find((x) => x.id === id) ?? null
        setSesion(s)
        setItems(itemsData)
        setSeguimiento(seg)
        setContenedores(conts)
        setContenedorId(s?.contenedor_id ?? '')
        setFacturaPara(s?.nombre_cliente ?? '')
        if (s?.cliente_id) {
          const c = await getCliente(s.cliente_id).catch(() => null)
          if (activo) setCliente(c)
        }
      } finally {
        if (activo) setCargando(false)
      }
    }
    cargar()
    return () => {
      activo = false
    }
  }, [id, recargarTick])

  const totales = useMemo(() => {
    const totalRmb = items.reduce((acc, i) => acc + (i.total_rmb || 0), 0)
    const totalUsd = items.reduce((acc, i) => acc + (i.total_usd || 0), 0)
    const proveedores = new Set(items.map((i) => i.supplier_nombre).filter(Boolean)).size
    return { totalRmb, totalUsd, proveedores }
  }, [items])

  const fmt = (n: number) => n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

  // Descarga el PDF/Excel de la cotización (Safari: abrir la pestaña dentro del toque).
  // `boton` es solo para saber qué botón mostrar como "Generando…" (el de Imprimir
  // también descarga el Excel, pero no debe activar el botón "Excel").
  const descargar = async (tipo: 'pdf' | 'excel', boton: 'pdf' | 'excel' | 'imprimir' = tipo) => {
    setGenerando(boton)
    const ventana = window.open('', '_blank')
    try {
      const blob = tipo === 'pdf' ? await exportarCotizacionPDF(id, idioma) : await exportarCotizacionExcel(id, idioma)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = `Cotizacion_${sesion?.nombre_cliente ?? ''}_${idioma}.${tipo === 'pdf' ? 'pdf' : 'xlsx'}`
        a.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      ventana?.close()
      toast.error(t('detalle.errorDescargar'))
    } finally {
      setGenerando(null)
    }
  }

  // Genera la factura comercial en USD (PDF/Excel). El contenedor seleccionado
  // define la TRM; sin contenedor se usa el tipo de cambio de la cotización.
  const generarFactura = async (tipo: 'pdf' | 'excel') => {
    setGenerandoFactura(tipo)
    const ventana = window.open('', '_blank')
    try {
      const cid = contenedorId || null
      const opciones = { contenedor_id: cid, de: facturaDe.trim() || null, para: facturaPara.trim() || null }
      const blob = tipo === 'pdf' ? await exportarFacturaPDF(id, opciones) : await exportarFacturaExcel(id, opciones)
      const url = URL.createObjectURL(blob)
      if (ventana) {
        ventana.location.href = url
      } else {
        const a = document.createElement('a')
        a.href = url
        a.download = `Factura_${sesion?.nombre_cliente ?? ''}.${tipo === 'pdf' ? 'pdf' : 'xlsx'}`
        a.click()
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000)
      // La sesión queda vinculada al contenedor elegido: reflejarlo en el estado.
      if (cid) setSesion((prev) => (prev ? { ...prev, contenedor_id: cid } : prev))
    } catch {
      ventana?.close()
      toast.error(t('detalle.errorFactura'))
    } finally {
      setGenerandoFactura(null)
    }
  }

  // Admin y vendedora llegan desde la ficha de ESE cliente (Clientes.tsx): hay
  // que volver ahí, no a la lista completa de clientes (antes "Volver" mandaba
  // siempre a /clientes, así que tocaba volver a buscar y entrar al cliente).
  // Contadora llega desde el Historial, que no tiene ficha de cliente.
  const puedeVolverAlCliente = (rol === 'vendedora' || rol === 'admin') && !!sesion?.cliente_id
  const volverA = puedeVolverAlCliente
    ? `/clientes/${sesion!.cliente_id}`
    : rol === 'vendedora' || rol === 'admin'
      ? '/clientes'
      : '/historial'

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => navigate(volverA)}
          className="flex items-center gap-2 text-sm font-medium"
          style={{ color: 'var(--yuda-primary)' }}
        >
          <ArrowLeft size={16} />{' '}
          {puedeVolverAlCliente
            ? t('detalle.volverCliente', { nombre: sesion?.nombre_cliente })
            : rol === 'vendedora' || rol === 'admin'
              ? t('detalle.volverClientes')
              : t('detalle.volver')}
        </button>
      </div>

      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>
          {sesion?.nombre_cliente ?? t('detalle.titulo')}
        </h1>
        {sesion && (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {sesion.fecha} · {t('detalle.tipoCambio')}: {sesion.tipo_cambio_usd}
          </p>
        )}
      </div>

      {cargando ? (
        <p className="text-center" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('detalle.cargando')}
        </p>
      ) : !sesion ? (
        <p className="text-center" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('detalle.noEncontrada')}
        </p>
      ) : (
        <>
          {/* Totales: siempre visible, para orientarse sin importar la pestaña */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
            <MetricCard titulo={t('historial.items')} valor={items.length} icono={<Package size={20} />} color="var(--yuda-primary)" />
            <MetricCard titulo={t('historial.totalRmb')} valor={`¥ ${fmt(totales.totalRmb)}`} icono={<Coins size={20} />} color="var(--yuda-warning)" />
            <MetricCard titulo={t('historial.totalUsd')} valor={`$ ${fmt(totales.totalUsd)}`} icono={<DollarSign size={20} />} color="var(--yuda-success)" />
            <MetricCard titulo={t('detalle.tiendas')} valor={totales.proveedores} icono={<Store size={20} />} color="var(--yuda-accent)" />
          </div>

          {/* 3 pestañas: qué hacer con el pedido (proveedores/bodega) / la
              cotización que ve el cliente / el seguimiento del envío. Antes
              "Ver detalle" (esta pantalla) y "Gestionar pedido" (un panel
              aparte que se abría en la lista) eran dos cosas separadas y
              confusas -ahora es un solo lugar. */}
          <div className="flex gap-2 border-b" style={{ borderColor: 'var(--yuda-border)' }}>
            {(['gestion', 'cotizacion', 'seguimiento', 'cubicaje'] as const)
              .filter((tabId) => (tabId !== 'gestion' && tabId !== 'cubicaje') || rol === 'admin' || rol === 'vendedora')
              .map((tabId) => (
                <button
                  key={tabId}
                  type="button"
                  onClick={() => setTab(tabId)}
                  className="px-3 py-2 text-sm font-semibold"
                  style={{
                    color: tab === tabId ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
                    borderBottom: tab === tabId ? '2px solid var(--yuda-primary)' : '2px solid transparent',
                  }}
                >
                  {t(`detalle.tab.${tabId}`)}
                </button>
              ))}
          </div>

          {/* Pestaña "Gestión": qué hacer con el pedido, proveedores y bodega */}
          {tab === 'gestion' && (rol === 'admin' || rol === 'vendedora') && (
            <>
              {sesion.pedido_recibido_at ? (
                <GestionPedidoCliente sesion={sesion} onActualizar={recargar} />
              ) : (
                <div className="card">
                  <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {t('detalle.sinPedidoCliente')}
                  </p>
                </div>
              )}
            </>
          )}

          {/* Pestaña "Cubicaje": control de cubicaje del pedido frente al
              contenedor, y la conversación con bodega alrededor. */}
          {tab === 'cubicaje' && (rol === 'admin' || rol === 'vendedora') && <CubicajePanel sesionId={id} />}

          {/* Pestaña "Seguimiento": tracking del envío */}
          {tab === 'seguimiento' && (
            rol === 'admin' || rol === 'vendedora' ? (
              <SeguimientoEditor sesionId={id} />
            ) : (
              <section className="card">
                <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
                  {t('detalle.envio')}
                </h2>
                {seguimiento ? (
                  <SeguimientoTimeline seguimiento={seguimiento} />
                ) : (
                  <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {t('detalle.sinEnvio')}
                  </p>
                )}
              </section>
            )
          )}

          {/* Pestaña "Cotización": lo que se le cotizó al cliente (solo lectura) */}
          {tab === 'cotizacion' && (
          <>
          {/* Editar vuelve al panel donde se arma/corrige la cotización (OCR,
              productos, cantidades): solo tiene sentido desde esta pestaña,
              no desde Gestión o Seguimiento. */}
          {(esAdmin || rol === 'vendedora') && (
            <button
              type="button"
              onClick={() => navigate('/dashboard', { state: { sesion_id: id } })}
              className="flex items-center gap-2 self-start rounded-lg border px-3 py-1.5 text-sm font-medium"
              style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)' }}
            >
              <Pencil size={15} /> {t('detalle.editarPanel')}
            </button>
          )}
          {/* Descargar la cotización (PDF / Excel) — para Marcela y la contadora */}
          {items.length > 0 && (
            <section className="card flex flex-col gap-3">
              <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('detalle.descargarTitulo')}</h2>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('detalle.idioma')}:</span>
                {IDIOMAS.map((op) => (
                  <button
                    key={op.code}
                    type="button"
                    onClick={() => setIdioma(op.code)}
                    className="rounded-lg border px-3 py-1.5 text-sm font-medium"
                    style={
                      idioma === op.code
                        ? { borderColor: 'var(--yuda-primary)', backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }
                        : { borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-secondary)' }
                    }
                  >
                    {op.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => descargar('pdf')}
                  disabled={generando !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 16, padding: '0 20px' }}
                >
                  <FileText size={18} /> {generando === 'pdf' ? `${t('detalle.generando')} ${Math.round(pct)}%` : t('detalle.descargarPdf')}
                </button>
                <button
                  type="button"
                  onClick={() => descargar('excel')}
                  disabled={generando !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-success)', fontSize: 16, padding: '0 20px' }}
                >
                  <FileSpreadsheet size={18} /> {generando === 'excel' ? `${t('detalle.generando')} ${Math.round(pct)}%` : t('detalle.descargarExcel')}
                </button>
                <button
                  type="button"
                  onClick={() => descargar('excel', 'imprimir')}
                  disabled={generando !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg border font-semibold disabled:opacity-60"
                  style={{ borderColor: 'var(--yuda-primary)', color: 'var(--yuda-primary)', fontSize: 16, padding: '0 20px' }}
                >
                  <Printer size={18} /> {generando === 'imprimir' ? `${t('detalle.generando')} ${Math.round(pct)}%` : t('detalle.imprimir')}
                </button>
              </div>
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('detalle.imprimirAyuda')}</p>
            </section>
          )}

          {/* Generar la factura del cliente en USD: solo Marcela la usa, las
              vendedoras nunca hacen facturas. */}
          {items.length > 0 && esAdmin && (
            <section className="card flex flex-col gap-3">
              <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }} className="flex items-center gap-2">
                <Receipt size={18} /> {t('detalle.facturaTitulo')}
              </h2>
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('detalle.facturaAyuda')}</p>
              <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                <span className="flex items-center gap-1.5"><Ship size={15} /> {t('detalle.facturaContenedor')}</span>
                <select
                  value={contenedorId}
                  onChange={(e) => setContenedorId(e.target.value)}
                  className="rounded-lg border px-3 py-2 text-sm"
                  style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-primary)', maxWidth: 420 }}
                >
                  <option value="">
                    {t('detalle.facturaSinContenedor')} · {t('detalle.facturaTrm', { trm: sesion?.tipo_cambio_usd ?? '' })}
                  </option>
                  {contenedores.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.codigo} · {t('detalle.facturaTrm', { trm: c.trm_usd })}
                    </option>
                  ))}
                </select>
              </label>
              {/* De (FROM) y Para (TO) editables antes de generar */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('detalle.facturaDe')}
                  <textarea
                    value={facturaDe}
                    onChange={(e) => setFacturaDe(e.target.value)}
                    rows={3}
                    placeholder={t('detalle.facturaDePlaceholder')}
                    className="rounded-lg border px-3 py-2 text-sm"
                    style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-primary)' }}
                  />
                </label>
                <label className="flex flex-col gap-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('detalle.facturaPara')}
                  <textarea
                    value={facturaPara}
                    onChange={(e) => setFacturaPara(e.target.value)}
                    rows={3}
                    placeholder={t('detalle.facturaParaPlaceholder')}
                    className="rounded-lg border px-3 py-2 text-sm"
                    style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text-primary)' }}
                  />
                </label>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => generarFactura('pdf')}
                  disabled={generandoFactura !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-primary)', fontSize: 16, padding: '0 20px' }}
                >
                  <FileText size={18} /> {generandoFactura === 'pdf' ? `${t('detalle.generando')} ${Math.round(pctFactura)}%` : t('detalle.facturaPdf')}
                </button>
                <button
                  type="button"
                  onClick={() => generarFactura('excel')}
                  disabled={generandoFactura !== null}
                  className="flex min-h-[48px] items-center justify-center gap-2 rounded-lg font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-success)', fontSize: 16, padding: '0 20px' }}
                >
                  <FileSpreadsheet size={18} /> {generandoFactura === 'excel' ? `${t('detalle.generando')} ${Math.round(pctFactura)}%` : t('detalle.facturaExcel')}
                </button>
              </div>
            </section>
          )}

          {/* Ficha del cliente (solo lectura) */}
          {cliente && (
            <section className="card">
              <h2 className="mb-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
                {t('detalle.cliente')}
              </h2>
              <div className="grid gap-2 text-sm sm:grid-cols-2" style={{ color: 'var(--yuda-text)' }}>
                <p className="flex items-center gap-2">
                  <Building2 size={15} style={{ color: 'var(--yuda-text-secondary)' }} />
                  <strong>{cliente.nombre}</strong>
                  {cliente.empresa ? ` · ${cliente.empresa}` : ''}
                </p>
                {cliente.email && (
                  <p className="flex items-center gap-2">
                    <Mail size={15} style={{ color: 'var(--yuda-text-secondary)' }} /> {cliente.email}
                  </p>
                )}
                {cliente.telefono && (
                  <p className="flex items-center gap-2">
                    <Phone size={15} style={{ color: 'var(--yuda-text-secondary)' }} /> {cliente.telefono}
                  </p>
                )}
                {cliente.pais && <p className="flex items-center gap-2">📍 {cliente.pais}</p>}
              </div>
            </section>
          )}

          {/* Pedido del cliente: cajas que pidió y sus notas (componente compartido) */}
          {items.length > 0 && <PedidoCliente sesion={sesion} items={items} mostrarVacio />}

          {/* Productos (solo lectura) */}
          <section className="card overflow-x-auto p-0">
            <h2 className="px-4 pt-4" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
              {t('detalle.productos')}
            </h2>
            {items.length === 0 ? (
              <p className="px-4 py-6 text-center" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('detalle.sinProductos')}
              </p>
            ) : (
              <table className="mt-3 w-full text-sm">
                <thead style={{ backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' }}>
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">{t('detalle.descripcion')}</th>
                    <th className="px-4 py-3 text-left font-semibold">{t('detalle.proveedor')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('detalle.ctns')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('detalle.precioRmb')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('historial.totalRmb')}</th>
                    <th className="px-4 py-3 text-right font-semibold">{t('historial.totalUsd')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => (
                    <tr key={item.id} style={{ backgroundColor: i % 2 === 0 ? 'var(--yuda-white)' : '#F9F9F7' }}>
                      <td className="px-4 py-3 font-medium">
                        {item.descripcion_es || item.descripcion_en || item.item_no || '—'}
                      </td>
                      <td className="px-4 py-3">{item.supplier_nombre || '—'}</td>
                      <td className="px-4 py-3 text-right">{item.ctns}</td>
                      <td className="px-4 py-3 text-right">{item.price_rmb.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">{item.total_rmb.toFixed(2)}</td>
                      <td className="px-4 py-3 text-right">{item.total_usd.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
          </>
          )}
        </>
      )}
    </div>
  )
}

export default CotizacionDetalle
