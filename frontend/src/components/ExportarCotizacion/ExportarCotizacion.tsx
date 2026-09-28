import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { AlertTriangle, CheckCircle2, Link as LinkIcon, Send, UserCheck } from 'lucide-react'
import { exportarCotizacionExcel, exportarCotizacionPDF } from '../../api/packing'
import { enviarACliente, getClientes, vincularCliente } from '../../api/clientes'
import { usePackingStore } from '../../store/packingStore'
import SelectorCliente from '../SelectorCliente/SelectorCliente'
import type { Cliente } from '../../types/cliente'

interface ExportarCotizacionProps {
  sesion_id: string
  nombre_cliente: string
  clienteIdInicial: string | null
  enviadaInicial: boolean
  // Sin esto, quien use este componente (el asistente de cotización) se queda
  // con el valor de cuando se montó: si la vendedora asigna o envía acá y ese
  // padre usa ese dato para algo (ej. bloquear "Terminar"), seguía viendo el
  // estado viejo aunque el problema ya estuviera resuelto.
  onEstadoCambiado?: (estado: { clienteId: string | null; enviada: boolean }) => void
}

// Mismo orden y claves que CLAVES_COLUMNAS en cotizacion_service.py: cambiar
// una lista sin la otra hace que las columnas salgan desordenadas o con
// nombres sin traducir.
const CLAVES_COLUMNAS = [
  'numero', 'fecha_recibo', 'shipping_mark', 'foto', 'referencia', 'codigo',
  'desc_es', 'desc_en', 'desc_zh', 'material', 'uso',
  'cajas', 'uds_caja', 'unidad', 'cant_total',
  'precio_rmb', 'total_rmb', 'precio_usd', 'total_usd',
  'largo', 'ancho', 'alto', 'cbm', 't_cbm',
  'peso', 'peso_total', 'mqt', 'marca',
] as const

// Propias de una cotización de bolsos: solo se muestran como opción (y solo
// salen en el documento) cuando la sesión es de ese tipo. Mismo orden que
// CLAVES_COLUMNAS_BOLSOS en cotizacion_service.py.
const CLAVES_COLUMNAS_BOLSOS = [
  'tamano', 'empaque', 'etiqueta', 'herrajes', 'riata',
  'minimo_cajas_tienda', 'minimo_piezas_caja_tienda',
] as const

// Sin foto o referencia el cliente no puede identificar el producto: no se
// pueden desmarcar (el backend también las fuerza, por si acaso).
const COLUMNAS_OBLIGATORIAS = new Set(['foto', 'referencia'])

const IDIOMAS = [
  { code: 'es', label: 'ES' },
  { code: 'en', label: 'EN' },
  { code: 'zh', label: '中文' },
]

// Descarga directa al dispositivo, sin abrir pestaña: antes se abría una
// pestaña en blanco DESDE el clic (truco para que Safari no la bloqueara) y
// se quedaba así, en blanco, mientras el documento se generaba -daba la
// sensación de que no había pasado nada. Ahora no hay pestaña que mirar: el
// archivo cae directo a Descargas cuando está listo, igual en todos lados.
function descargarArchivo(blob: Blob, nombre: string) {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombre
  enlace.click()
  setTimeout(() => URL.revokeObjectURL(url), 60000)
}

function ExportarCotizacion({
  sesion_id,
  nombre_cliente,
  clienteIdInicial,
  enviadaInicial,
  onEstadoCambiado,
}: ExportarCotizacionProps) {
  const { t, i18n } = useTranslation()
  const inicial = ['es', 'en', 'zh'].includes(i18n.language) ? i18n.language : 'es'
  const [idioma, setIdioma] = useState(inicial)
  // Genera Excel + PDF y envía al cliente de una sola vez: antes eran tres
  // acciones sueltas (dos botones de descarga y una tarjeta aparte para
  // enviar), y nada avisaba si de verdad ya se había revisado todo.
  const [generando, setGenerando] = useState(false)
  // Generar el documento (con las fotos incrustadas) puede tardar varios
  // segundos y no hay forma de saber el avance real desde el navegador (es
  // una sola respuesta del servidor, no algo que se pueda medir por partes).
  // Este porcentaje avanza solo hacia un tope, igual que en la carga masiva:
  // no promete un tiempo exacto, pero deja claro que sigue en marcha.
  const [pct, setPct] = useState(0)
  useEffect(() => {
    setPct(0)
  }, [generando])
  useEffect(() => {
    if (!generando) return
    const id = setInterval(() => {
      setPct((v) => (v >= 95 ? v : v + (95 - v) * 0.08))
    }, 200)
    return () => clearInterval(id)
  }, [generando])
  const [error, setError] = useState<string | null>(null)
  const [confirmado, setConfirmado] = useState(false)
  // Qué columnas va a traer el documento. Todas marcadas por defecto (incluidas
  // las de bolsos: si la sesión no es de bolsos, el backend las ignora igual,
  // así no hace falta reiniciar el estado según el tipo de cotización).
  const [columnasActivas, setColumnasActivas] = useState<Set<string>>(
    () => new Set([...CLAVES_COLUMNAS, ...CLAVES_COLUMNAS_BOLSOS]),
  )
  const toggleColumna = (clave: string) => {
    if (COLUMNAS_OBLIGATORIAS.has(clave)) return
    setColumnasActivas((prev) => {
      const siguiente = new Set(prev)
      if (siguiente.has(clave)) siguiente.delete(clave)
      else siguiente.add(clave)
      return siguiente
    })
  }

  // Cliente al que se le envía esta cotización (venido de ClienteEnvio, ahora
  // fusionado acá: revisar el documento y mandárselo al cliente es una sola
  // decisión, no dos pantallas separadas).
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [cargandoClientes, setCargandoClientes] = useState(true)
  const [errorClientes, setErrorClientes] = useState(false)
  const [clienteId, setClienteId] = useState<string | null>(clienteIdInicial)
  const [enviada, setEnviada] = useState(enviadaInicial)
  const [seleccion, setSeleccion] = useState('')
  const [asignando, setAsignando] = useState(false)

  const cargarClientes = () => {
    setCargandoClientes(true)
    setErrorClientes(false)
    getClientes()
      .then(setClientes)
      .catch(() => setErrorClientes(true))
      .finally(() => setCargandoClientes(false))
  }

  useEffect(() => {
    cargarClientes()
  }, [])

  // Sincroniza con la cotización seleccionada
  useEffect(() => {
    setClienteId(clienteIdInicial)
    setEnviada(enviadaInicial)
  }, [clienteIdInicial, enviadaInicial, sesion_id])

  // Avisa al padre en cada cambio real (asignar, desvincular, enviar), no
  // solo al montar: así el que lo use siempre tiene el estado en vivo.
  useEffect(() => {
    onEstadoCambiado?.({ clienteId, enviada })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteId, enviada])

  const clienteActual = clientes.find((c) => c.id === clienteId) || null

  const asignarCliente = async () => {
    if (!seleccion) return
    setAsignando(true)
    try {
      await vincularCliente(sesion_id, seleccion)
      setClienteId(seleccion)
      toast.success(t('envio.clienteAsignado'))
    } catch {
      toast.error(t('envio.errorAsignar'))
    } finally {
      setAsignando(false)
    }
  }

  const desvincularCliente = async () => {
    setAsignando(true)
    try {
      await vincularCliente(sesion_id, null)
      setClienteId(null)
      setEnviada(false)
      setSeleccion('')
    } catch {
      toast.error(t('envio.errorAsignar'))
    } finally {
      setAsignando(false)
    }
  }

  const items = usePackingStore((s) => s.items)
  const esBolsos = usePackingStore((s) => s.sesionActual?.tipo_cotizacion === 'bolsos')
  const clavesAMostrar = esBolsos ? [...CLAVES_COLUMNAS, ...CLAVES_COLUMNAS_BOLSOS] : CLAVES_COLUMNAS
  // Foto 1 (producto con datos): obligatoria para generar. La cargan el OCR.
  const sinFotoDatos = items.filter((i) => !i.foto_url).length
  // Datos clave que deberían haberse extraído (precio + alguna descripción).
  const sinDatos = items.filter(
    (i) => !i.price_rmb || !(i.descripcion_es || i.descripcion_en || i.descripcion_zh),
  ).length
  const sinProductos = items.length === 0
  // No se puede generar sin productos, sin la foto de datos en todos, ni sin confirmar.
  const bloqueado = sinProductos || sinFotoDatos > 0 || !confirmado
  // Antes el boton bloqueado simplemente no respondia (disabled nativo no dispara
  // onClick): habia que leer la lista de arriba para entender por que. Ahora, al
  // tocarlo, dice exactamente cual de los tres motivos falta.
  const motivoBloqueo = sinProductos
    ? t('cotizacion.sinProductos')
    : sinFotoDatos > 0
      ? t('cotizacion.faltaFotoDatos', { n: sinFotoDatos })
      : !confirmado
        ? t('cotizacion.faltaConfirmar')
        : null

  // Un solo botón: genera Excel y PDF, descarga los dos y avisa al cliente
  // por su portal, todo en el mismo clic. Antes eran tres acciones sueltas y
  // nada obligaba a revisar antes de mandarle algo mal al cliente.
  const generarYEnviar = async () => {
    if (bloqueado) {
      if (motivoBloqueo) toast.error(motivoBloqueo)
      return
    }
    setError(null)
    setGenerando(true)
    try {
      const columnas = Array.from(columnasActivas)
      const [excelBlob, pdfBlob] = await Promise.all([
        exportarCotizacionExcel(sesion_id, idioma, columnas),
        exportarCotizacionPDF(sesion_id, idioma, columnas),
      ])
      descargarArchivo(excelBlob, `Cotizacion_${nombre_cliente}_${idioma}.xlsx`)
      descargarArchivo(pdfBlob, `Cotizacion_${nombre_cliente}_${idioma}.pdf`)
      await enviarACliente(sesion_id)
      setEnviada(true)
      toast.success(t('cotizacion.generadaYEnviada'))
    } catch {
      setError(t('cotizacion.error'))
    } finally {
      setGenerando(false)
    }
  }

  return (
    <div className="card flex flex-col gap-4">
      <h2 style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>{t('cotizacion.titulo')}</h2>
      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('cotizacion.ayuda')}</p>

      {/* Sin cliente asignado todavía: hay que elegir uno antes de poder
          revisar y enviar el documento (una cotización libre nace sin
          cliente, o se puede haber desvinculado). */}
      {!clienteActual ? (
        <div className="flex flex-col gap-3">
          {cargandoClientes ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('dashboard.cargandoClientes')}
            </p>
          ) : errorClientes ? (
            <div className="flex flex-col items-start gap-2 p-4" style={{ borderRadius: 12, backgroundColor: '#FEF2F2' }}>
              <p className="text-sm" style={{ color: 'var(--yuda-error-dark)' }}>{t('dashboard.errorCargarClientes')}</p>
              <button
                type="button"
                onClick={cargarClientes}
                className="flex items-center gap-2 font-semibold text-white"
                style={{ minHeight: 40, backgroundColor: 'var(--yuda-error)', borderRadius: 8, padding: '0 14px', fontSize: 14 }}
              >
                {t('dashboard.reintentarCargarClientes')}
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('envio.elegirCliente')}</span>
              <SelectorCliente clientes={clientes} valor={seleccion} onElegir={setSeleccion} />
              <button
                type="button"
                onClick={asignarCliente}
                disabled={asignando || !seleccion}
                className="flex items-center justify-center gap-2 self-start font-semibold text-white disabled:opacity-60"
                style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
              >
                <LinkIcon size={18} /> {t('envio.asignar')}
              </button>
              {clientes.length === 0 && (
                <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('envio.sinClientesParaAsignar')}{' '}
                  <Link to="/clientes" style={{ color: 'var(--yuda-primary)', fontWeight: 600, textDecoration: 'underline' }}>
                    {t('envio.irAClientes')}
                  </Link>
                </p>
              )}
            </div>
          )}
        </div>
      ) : (
        <>
          {/* Cliente asignado */}
          <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl p-3" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
            <div className="flex items-center gap-2">
              <UserCheck size={18} style={{ color: 'var(--yuda-primary)' }} />
              <span className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>{clienteActual.nombre}</span>
              <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{clienteActual.email}</span>
            </div>
            {!enviada && (
              <button type="button" onClick={desvincularCliente} className="text-sm font-medium" style={{ color: 'var(--yuda-error)' }}>
                {t('envio.cambiar')}
              </button>
            )}
          </div>

          {/* Selector de idioma */}
          <div className="flex gap-1">
            {IDIOMAS.map((idi) => {
              const activo = idioma === idi.code
              return (
                <button
                  key={idi.code}
                  type="button"
                  onClick={() => setIdioma(idi.code)}
                  style={{
                    borderRadius: 6,
                    backgroundColor: activo ? 'var(--yuda-primary)' : 'transparent',
                    color: activo ? 'var(--yuda-white)' : 'var(--yuda-text-secondary)',
                    padding: '6px 14px',
                    fontSize: 14,
                    fontWeight: 600,
                  }}
                >
                  {idi.label}
                </button>
              )
            })}
          </div>

          {/* Qué columnas va a traer el documento. Todas activas por defecto,
              elegirlas es opcional. */}
          <div className="rounded-xl border p-3" style={{ borderColor: 'var(--yuda-border)' }}>
            <p className="mb-1 text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
              {t('cotizacion.columnasTitulo')}
            </p>
            <p className="mb-2 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('cotizacion.columnasAyuda')}
            </p>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 sm:grid-cols-3">
              {clavesAMostrar.map((clave) => {
                const obligatoria = COLUMNAS_OBLIGATORIAS.has(clave)
                return (
                  <label
                    key={clave}
                    className="flex items-center gap-1.5 text-sm"
                    style={{ color: obligatoria ? 'var(--yuda-text-secondary)' : 'var(--yuda-accent)' }}
                  >
                    <input
                      type="checkbox"
                      checked={obligatoria || columnasActivas.has(clave)}
                      disabled={obligatoria}
                      onChange={() => toggleColumna(clave)}
                      style={{ width: 15, height: 15, flexShrink: 0 }}
                    />
                    <span className="truncate">
                      {t(`cotizacion.columnas.${clave}`)}
                      {obligatoria && <span className="text-xs italic"> ({t('cotizacion.columnaObligatoria')})</span>}
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          {/* Antes de generar: confirmar extracción y fotos según su propósito.
              El botón de abajo solo se habilita una vez se marca este check. */}
          <div className="rounded-xl border p-3" style={{ borderColor: 'var(--yuda-border)', backgroundColor: '#F9FAFB' }}>
            <p className="mb-2 text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
              {t('cotizacion.confirmTitulo')}
            </p>
            {sinProductos ? (
              <p className="flex items-center gap-2 text-sm" style={{ color: 'var(--yuda-warning-dark)' }}>
                <AlertTriangle size={15} /> {t('cotizacion.sinProductos')}
              </p>
            ) : (
              <div className="flex flex-col gap-1.5 text-sm">
                <p style={{ color: 'var(--yuda-text-secondary)' }}>{t('cotizacion.prodCount', { n: items.length })}</p>
                {sinFotoDatos > 0 ? (
                  <p className="flex items-center gap-2" style={{ color: 'var(--yuda-error)' }}>
                    <AlertTriangle size={15} /> {t('cotizacion.faltaFotoDatos', { n: sinFotoDatos })}
                  </p>
                ) : (
                  <p className="flex items-center gap-2" style={{ color: 'var(--yuda-success)' }}>
                    <CheckCircle2 size={15} /> {t('cotizacion.fotoDatosOk')}
                  </p>
                )}
                {sinDatos > 0 && (
                  <p className="flex items-center gap-2" style={{ color: 'var(--yuda-warning-dark)' }}>
                    <AlertTriangle size={15} /> {t('cotizacion.revisarDatos', { n: sinDatos })}
                  </p>
                )}
                <label className="mt-1 flex items-start gap-2" style={{ color: 'var(--yuda-accent)' }}>
                  <input
                    type="checkbox"
                    checked={confirmado}
                    onChange={(e) => setConfirmado(e.target.checked)}
                    style={{ marginTop: 3, width: 16, height: 16 }}
                  />
                  <span>{t('cotizacion.confirmCheck')}</span>
                </label>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={generarYEnviar}
            disabled={generando}
            aria-disabled={bloqueado}
            className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
            style={{ minHeight: 52, borderRadius: 8, fontSize: 16, backgroundColor: 'var(--yuda-success)', opacity: bloqueado ? 0.6 : 1 }}
          >
            {generando ? (
              `${t('cotizacion.generando')} ${Math.round(pct)}%`
            ) : (
              <>
                <Send size={18} /> {t('cotizacion.generarYEnviar')}
              </>
            )}
          </button>

          {enviada && (
            <div className="rounded-xl p-3 text-sm" style={{ backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }}>
              <p className="flex items-center gap-2 font-semibold">
                <UserCheck size={16} /> {t('envio.yaEnviada')}
              </p>
              <p className="mt-1">
                {t('envio.trackingEnClientes')}{' '}
                <Link to="/clientes" style={{ color: '#047857', fontWeight: 600, textDecoration: 'underline' }}>
                  {t('envio.irAClientes')}
                </Link>
              </p>
            </div>
          )}

          {error && <p className="text-center text-sm" style={{ color: 'var(--yuda-error)' }}>{error}</p>}
        </>
      )}
    </div>
  )
}

export default ExportarCotizacion
