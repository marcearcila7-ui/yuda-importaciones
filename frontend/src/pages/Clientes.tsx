import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import axios from 'axios'
import { AlertCircle, ArrowLeft, Check, ChevronDown, ChevronRight, Copy, Eye, EyeOff, FileText, KeyRound, Package, Plus, RefreshCw, Search, ShoppingBag, Trash2, UserPlus, UserRound, Users, Wallet, X } from 'lucide-react'
import { usePackingStore } from '../store/packingStore'
import { getConfiguracion } from '../api/admin'
import {
  actualizarCliente,
  buscarContable,
  descargarEstadoCuentaContablePdf,
  eliminarCliente,
  getClientes,
  getClientesNoSincronizados,
  getCotizacionesCliente,
  importarContable,
  importarContableUno,
  previewImportarContable,
  quitarEstadoCuentaOficial,
  resetPasswordCliente,
  subirEstadoCuentaOficial,
} from '../api/clientes'
import { eliminarSesion } from '../api/packing'
import { getEquipo } from '../api/admin'
import { useAuthStore } from '../store/authStore'
import { confirmar } from '../store/confirmStore'
import type { Cliente, ContableClientePreview } from '../types/cliente'
import type { Sesion } from '../types/packing'
import type { EquipoResponse } from '../types/equipo'

const numeroCot = (s: Sesion) =>
  `YUDA-${(s.fecha || '').replace(/-/g, '')}-${s.id.slice(0, 6).toUpperCase()}`

// Clasifica una cotización en una sola etapa, para que la vendedora sepa de
// un vistazo qué le falta a cada una en vez de leer 3 campos sueltos
// (enviada_cliente, pedido_estado, estado_envio) y adivinar qué significan
// juntos.
type EtapaCot = 'borrador' | 'con_cliente' | 'listas_bodega' | 'en_bodega' | 'en_camino' | 'entregadas'

// "proveedor_recibio"/"en_bodega" NO están en camino todavía: la mercancía
// sigue en China, con el proveedor o en la bodega de YUDA siendo revisada.
// Solo "en_transito"/"en_destino" es que ya salió de verdad hacia el cliente.
const ETAPAS_EN_BODEGA = ['proveedor_recibio', 'en_bodega']
const ETAPAS_EN_CAMINO = ['en_transito', 'en_destino']

function etapaDeCotizacion(s: Sesion): EtapaCot {
  if (!s.enviada_cliente) return 'borrador'
  if (s.estado_envio === 'entregado') return 'entregadas'
  if (s.estado_envio && ETAPAS_EN_CAMINO.includes(s.estado_envio)) return 'en_camino'
  if (s.estado_envio && ETAPAS_EN_BODEGA.includes(s.estado_envio)) return 'en_bodega'
  if (s.pedido_estado === 'confirmado') return 'listas_bodega'
  return 'con_cliente'
}

// Orden real del pipeline, para poder dibujarlo como una secuencia (no solo
// una etiqueta suelta) y para saber qué etapas ya se "pasaron".
const ETAPAS_ORDEN: EtapaCot[] = ['borrador', 'con_cliente', 'listas_bodega', 'en_bodega', 'en_camino', 'entregadas']

// Un color propio por etapa -antes "con_cliente", "en_camino" y "entregadas"
// compartían el mismo verde, y no se distinguían de un vistazo.
const COLOR_ETAPA: Record<EtapaCot, { bg: string; fg: string }> = {
  borrador: { bg: '#F3F4F6', fg: 'var(--yuda-text-secondary)' },
  con_cliente: { bg: 'var(--yuda-primary-soft)', fg: 'var(--yuda-primary)' },
  listas_bodega: { bg: 'var(--yuda-warning-soft)', fg: 'var(--yuda-warning-dark)' },
  en_bodega: { bg: 'var(--yuda-primary)', fg: 'var(--yuda-white)' },
  en_camino: { bg: 'var(--yuda-primary-dark)', fg: 'var(--yuda-white)' },
  entregadas: { bg: 'var(--yuda-success-soft)', fg: 'var(--yuda-success)' },
}

// Pipeline visual: un punto por etapa, unidos por una línea. Las que ya se
// pasaron quedan llenas, la actual se ve más grande con su propio color, y
// las que faltan quedan vacías -de un vistazo se ve dónde va la cotización,
// no solo el nombre suelto de la etapa.
function PipelineEtapa({ etapa }: { etapa: EtapaCot }) {
  const idx = ETAPAS_ORDEN.indexOf(etapa)
  return (
    <span className="inline-flex items-center" aria-hidden="true">
      {ETAPAS_ORDEN.map((et, i) => (
        <span key={et} className="inline-flex items-center">
          <span
            className="flex-shrink-0 rounded-full"
            style={
              i === idx
                ? { width: 9, height: 9, backgroundColor: COLOR_ETAPA[et].fg === 'var(--yuda-white)' ? 'var(--yuda-primary)' : COLOR_ETAPA[et].fg }
                : i < idx
                  ? { width: 6, height: 6, backgroundColor: 'var(--yuda-primary)' }
                  : { width: 6, height: 6, border: '1.5px solid var(--yuda-border)' }
            }
          />
          {i < ETAPAS_ORDEN.length - 1 && (
            <span
              className="flex-shrink-0"
              style={{ width: 8, height: 2, backgroundColor: i < idx ? 'var(--yuda-primary)' : 'var(--yuda-border)' }}
            />
          )}
        </span>
      ))}
    </span>
  )
}

// Genera una contraseña temporal legible (sin caracteres ambiguos) para reenviar
function generarPassword(): string {
  const abc = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789'
  const arr = new Uint32Array(10)
  crypto.getRandomValues(arr)
  return Array.from(arr, (n) => abc[n % abc.length]).join('') + '*'
}

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[var(--yuda-primary)] focus:outline-none'

function Clientes() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const rolUsuario = useAuthStore((s) => s.usuario?.rol)
  const esAdmin = rolUsuario === 'admin'
  // Lo contable (estado de cuenta) es exclusivo de Marcela y contabilidad; la
  // vendedora no debe ver saldos ni movimientos de dinero de sus clientes.
  const puedeVerCuenta = rolUsuario === 'admin' || rolUsuario === 'contadora'
  const crearSesion = usePackingStore((s) => s.crearSesion)
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [cargandoClientes, setCargandoClientes] = useState(true)
  const [errorClientes, setErrorClientes] = useState(false)
  const [copiadoLink, setCopiadoLink] = useState(false)
  // Atajo "+ Nueva cotización" desde la ficha del cliente: se salta elegir
  // cliente (ya estamos en el suyo), solo falta decidir qué se va a cotizar.
  const [eligiendoTipoNueva, setEligiendoTipoNueva] = useState(false)
  const [creandoTipoNueva, setCreandoTipoNueva] = useState<'productos' | 'bolsos' | null>(null)
  // Contraseña recién generada por cliente (solo en memoria, para reenviarla)
  const [nuevasPass, setNuevasPass] = useState<Record<string, string>>({})
  // El portal de clientes vive en un dominio aparte del cotizador
  // (usuarios.yudaimportaciones.com, ver DestinoPorDefecto en App.tsx): con
  // window.location.origin acá se armaba mal (cotizador.yudaimportaciones.com/
  // portal/login), un link que ya no existe. En desarrollo local sigue siendo
  // el mismo origin, porque ahí no hay dos dominios separados.
  const portalUrl = import.meta.env.PROD
    ? 'https://usuarios.yudaimportaciones.com/portal/login'
    : `${window.location.origin}/portal/login`

  // Un solo cliente abierto a la vez, en su propia pantalla -y ahora con su
  // propia URL ("/clientes/:clienteId"), no solo un estado en memoria. Sin
  // esto, refrescar la página (o el botón atrás del navegador) devolvía
  // siempre a la lista, sin importar qué se estuviera viendo.
  const { clienteId: clienteAbiertoId } = useParams<{ clienteId: string }>()
  const [busqueda, setBusqueda] = useState('')
  // Solo para Marcela: a que vendedora pertenece cada cliente, y el filtro.
  // Antes esto vivia en una pagina aparte, "Equipo", que mostraba los mismos
  // clientes pero agrupados. Dos listas de lo mismo confunden mas de lo que ayudan.
  const [equipo, setEquipo] = useState<EquipoResponse | null>(null)
  const [filtroVendedora, setFiltroVendedora] = useState('')
  const [verInactivos, setVerInactivos] = useState(false)
  const [cotizaciones, setCotizaciones] = useState<Record<string, Sesion[]>>({})
  // La ficha del cliente mezclaba identidad, acceso al portal y todas sus
  // cotizaciones en una sola pantalla larga: para una usuaria no técnica era
  // "un muro de información" sin saber qué mirar primero. Ahora son 3
  // pestañas, cada una respondiendo una sola pregunta a la vez.
  // Cotizaciones primero: es lo que la vendedora revisa a diario. Info y
  // Portal son de referencia/configuración, se consultan mucho menos seguido.
  const [tabCliente, setTabCliente] = useState<'cotizaciones' | 'info' | 'acceso'>('cotizaciones')
  // Dentro de "Cotizaciones": por etapa, para no mezclar borradores con lo
  // que ya está en camino. "todas" no filtra, solo agrupa visualmente.
  const [subTabCot, setSubTabCot] = useState<'todas' | EtapaCot>('todas')

  // Al entrar a un cliente (por click, por atrás/adelante del navegador, o
  // por refrescar con esa URL abierta) siempre arranca en la misma pestaña y
  // trae sus cotizaciones: nada queda "recordado" de una visita anterior que
  // pueda mostrarse sin que la vendedora lo haya pedido.
  useEffect(() => {
    if (!clienteAbiertoId) return
    setTabCliente('cotizaciones')
    setSubTabCot('todas')
    window.scrollTo({ top: 0, behavior: 'smooth' })
    if (cotizaciones[clienteAbiertoId] === undefined) {
      getCotizacionesCliente(clienteAbiertoId)
        .then((cots) => setCotizaciones((m) => ({ ...m, [clienteAbiertoId]: cots })))
        .catch(() => setCotizaciones((m) => ({ ...m, [clienteAbiertoId]: [] })))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clienteAbiertoId])

  const abrirCliente = (c: Cliente) => {
    navigate(`/clientes/${c.id}`)
  }

  const volverALista = () => {
    navigate('/clientes')
  }

  const recargarCotizaciones = (clienteId: string) => {
    getCotizacionesCliente(clienteId)
      .then((cots) => setCotizaciones((m) => ({ ...m, [clienteId]: cots })))
      .catch(() => {})
  }

  // Crea la cotización ya asignada a este cliente (sin el paso de buscarlo en
  // una lista, porque ya estamos en su ficha) y entra directo a la pantalla
  // de fotos. Mismo tipo de cambio por defecto que usa el asistente normal.
  const iniciarNuevaCotizacion = async (cliente: Cliente, tipo: 'productos' | 'bolsos') => {
    setCreandoTipoNueva(tipo)
    let tipoCambio = 6.7
    try {
      const cfg = await getConfiguracion()
      tipoCambio = cfg.tipo_cambio_usd
    } catch {
      // se usa el valor por defecto de arriba
    }
    await crearSesion(cliente.nombre, tipoCambio, cliente.id, tipo)
    setCreandoTipoNueva(null)
    const error = usePackingStore.getState().error
    if (error) {
      toast.error(error)
      return
    }
    setEligiendoTipoNueva(false)
    // Se manda el cliente de origen (para poder volver a su ficha si se
    // cancela o se elimina la cotización) y su sesion_id (para que Dashboard
    // no la borre al entrar: a Marcela, si llega sin sesion_id, le limpia el
    // escritorio por si quedó una cotización vieja abierta de antes).
    const nuevaSesion = usePackingStore.getState().sesionActual
    navigate('/dashboard', { state: { sesion_id: nuevaSesion?.id, clienteOrigenId: cliente.id } })
  }

  // Borrar una cotización del cliente. Si ya se la habían enviado, también deja
  // de verla en su portal.
  const eliminarCotizacion = async (s: Sesion, clienteId: string) => {
    const ok = await confirmar({
      mensaje: t('clientes.confirmarEliminarCotizacion', { numero: numeroCot(s) }),
      peligro: true,
      textoConfirmar: t('clientes.eliminarCotizacion'),
    })
    if (!ok) return
    try {
      await eliminarSesion(s.id)
      toast.success(t('clientes.cotizacionEliminada'))
      recargarCotizaciones(clienteId)
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      toast.error(typeof detalle === 'string' ? detalle : t('clientes.errorEliminarCotizacion'))
    }
  }


  const cargar = () => {
    setCargandoClientes(true)
    setErrorClientes(false)
    getClientes()
      .then(setClientes)
      .catch(() => setErrorClientes(true))
      .finally(() => setCargandoClientes(false))
  }

  useEffect(() => {
    cargar()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Marcela ve todos los clientes: necesita saber de quien es cada uno y poder
  // filtrar. Las vendedoras solo ven los suyos, asi que no hace falta pedirlo.
  useEffect(() => {
    if (!esAdmin) return
    getEquipo()
      .then(setEquipo)
      .catch(() => setEquipo({ vendedoras: [] }))
  }, [esAdmin])

  const toggleActivo = async (c: Cliente) => {
    try {
      await actualizarCliente(c.id, { activo: !c.activo })
      cargar()
    } catch {
      toast.error(t('clientes.errorActualizar'))
    }
  }

  // Reasignar la vendedora dueña (diagnóstico #2): el backend ya lo permitía
  // (PATCH /clientes/{id} con vendedora_id, admin-only), pero no había ningún
  // botón en la UI para hacerlo — solo el de "compartir" (agregar
  // colaboradora), que es una cosa distinta.
  const [editandoDuena, setEditandoDuena] = useState(false)
  const [duenaInput, setDuenaInput] = useState('')
  const [guardandoDuena, setGuardandoDuena] = useState(false)

  const guardarDuena = async (c: Cliente) => {
    if (!duenaInput) return
    setGuardandoDuena(true)
    try {
      await actualizarCliente(c.id, { vendedora_id: duenaInput })
      toast.success(t('clientes.duenaGuardada'))
      setEditandoDuena(false)
      cargar()
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? (err.response?.data?.detail as string | undefined) : undefined
      toast.error(detalle || t('clientes.errorDuena'))
    } finally {
      setGuardandoDuena(false)
    }
  }

  // Asignar vendedora a un contacto importado pendiente, directo desde la
  // lista de espera (sin tener que abrir su ficha).
  const [asignandoPendiente, setAsignandoPendiente] = useState<Record<string, boolean>>({})
  const asignarPendiente = async (clienteId: string, vendedoraId: string) => {
    if (!vendedoraId) return
    setAsignandoPendiente((s) => ({ ...s, [clienteId]: true }))
    try {
      await actualizarCliente(clienteId, { vendedora_id: vendedoraId })
      toast.success(t('clientes.duenaGuardada'))
      cargar()
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? (err.response?.data?.detail as string | undefined) : undefined
      toast.error(detalle || t('clientes.errorDuena'))
    } finally {
      setAsignandoPendiente((s) => ({ ...s, [clienteId]: false }))
    }
  }

  // Importar clientes de Yuda Contable (Fase 2): trae hacia acá los que ya
  // existen en la app de contabilidad y todavía no están en el cotizador.
  const [mostrarImportar, setMostrarImportar] = useState(false)
  const [previewContable, setPreviewContable] = useState<ContableClientePreview[]>([])
  const [cargandoPreview, setCargandoPreview] = useState(false)
  const [siglasSeleccionadas, setSiglasSeleccionadas] = useState<Set<string>>(new Set())
  const [importando, setImportando] = useState(false)

  const abrirImportar = async () => {
    setMostrarImportar((v) => !v)
    if (previewContable.length > 0) return
    setCargandoPreview(true)
    try {
      const datos = await previewImportarContable()
      setPreviewContable(datos)
      // Preselecciona solo los que todavía no existen: los que ya están no
      // hace falta tocarlos.
      setSiglasSeleccionadas(new Set(datos.filter((d) => !d.ya_existe).map((d) => d.sigla)))
    } catch {
      toast.error(t('clientes.errorPreviewContable'))
    } finally {
      setCargandoPreview(false)
    }
  }

  const toggleSigla = (sigla: string) =>
    setSiglasSeleccionadas((prev) => {
      const next = new Set(prev)
      if (next.has(sigla)) next.delete(sigla)
      else next.add(sigla)
      return next
    })

  const handleImportarContable = async () => {
    const ok = await confirmar({
      mensaje: t('clientes.confirmarImportarContable', { n: siglasSeleccionadas.size }),
      textoConfirmar: t('clientes.importar'),
    })
    if (!ok) return
    setImportando(true)
    try {
      const { creados, omitidos } = await importarContable(Array.from(siglasSeleccionadas))
      toast.success(t('clientes.contableImportado', { creados, omitidos }))
      const datos = await previewImportarContable()
      setPreviewContable(datos)
      setSiglasSeleccionadas(new Set())
      cargar()
    } catch {
      toast.error(t('clientes.errorImportarContable'))
    } finally {
      setImportando(false)
    }
  }

  // Estado de sincronización con Yuda Contable: todo, o el listado de lo que
  // falta (nombre + sigla) para importar desde acá. Se carga solo al entrar
  // (no hace falta que Marcela busque nada para verlo).
  const [noSincronizados, setNoSincronizados] = useState<ContableClientePreview[] | null>(null)
  const [cargandoNoSincronizados, setCargandoNoSincronizados] = useState(false)
  const [siglaSeleccionadaSync, setSiglaSeleccionadaSync] = useState('')

  const cargarNoSincronizados = async () => {
    setCargandoNoSincronizados(true)
    try {
      setNoSincronizados(await getClientesNoSincronizados())
    } catch {
      setNoSincronizados(null)
    } finally {
      setCargandoNoSincronizados(false)
    }
  }

  useEffect(() => {
    if (esAdmin) cargarNoSincronizados()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [esAdmin])

  // Búsqueda EN VIVO en Yuda Contable (a diferencia de la lista fija de
  // arriba, que hay que pedirme que la regenere a mano de vez en cuando).
  const [busquedaContable, setBusquedaContable] = useState('')
  const [resultadosContable, setResultadosContable] = useState<ContableClientePreview[] | null>(null)
  const [buscandoContable, setBuscandoContable] = useState(false)
  const [importandoUno, setImportandoUno] = useState<Record<string, boolean>>({})

  const buscarEnContable = async () => {
    const q = busquedaContable.trim()
    if (q.length < 2) return
    setBuscandoContable(true)
    try {
      setResultadosContable(await buscarContable(q))
    } catch {
      toast.error(t('clientes.errorBuscarContable'))
      setResultadosContable(null)
    } finally {
      setBuscandoContable(false)
    }
  }

  const importarUno = async (sigla: string) => {
    setImportandoUno((s) => ({ ...s, [sigla]: true }))
    try {
      await importarContableUno(sigla)
      toast.success(t('clientes.contableImportadoUno', { sigla }))
      setResultadosContable((prev) =>
        prev ? prev.map((r) => (r.sigla === sigla ? { ...r, ya_existe: true } : r)) : prev,
      )
      setNoSincronizados((prev) => (prev ? prev.filter((r) => r.sigla !== sigla) : prev))
      if (siglaSeleccionadaSync === sigla) setSiglaSeleccionadaSync('')
      cargar()
    } catch (err) {
      const detalle = axios.isAxiosError(err) ? (err.response?.data?.detail as string | undefined) : undefined
      toast.error(detalle || t('clientes.errorImportarContable'))
    } finally {
      setImportandoUno((s) => ({ ...s, [sigla]: false }))
    }
  }

  const eliminar = async (c: Cliente) => {
    const ok = await confirmar({
      mensaje: t('clientes.confirmarEliminar', { nombre: c.nombre }),
      peligro: true,
      textoConfirmar: t('clientes.eliminar'),
    })
    if (!ok) return
    try {
      await eliminarCliente(c.id)
      toast.success(t('clientes.eliminado'))
      cargar()
    } catch (err) {
      const estado = axios.isAxiosError(err) ? err.response?.status : null
      // 409: tiene cotizaciones enviadas y no se puede eliminar. En vez de dejar
      // a la vendedora sin salida, le ofrecemos desactivarlo en un clic.
      if (estado === 409) {
        if (await confirmar({ mensaje: t('clientes.ofrecerDesactivar', { nombre: c.nombre }), textoConfirmar: t('clientes.desactivar') })) {
          try {
            await actualizarCliente(c.id, { activo: false })
            toast.success(t('clientes.desactivado', { nombre: c.nombre }))
            cargar()
          } catch {
            toast.error(t('clientes.errorActualizar'))
          }
        }
        return
      }
      const detalle = axios.isAxiosError(err) ? err.response?.data?.detail : null
      toast.error(typeof detalle === 'string' ? detalle : t('clientes.errorEliminar'))
    }
  }

  const copiarLink = async () => {
    try {
      await navigator.clipboard.writeText(portalUrl)
      setCopiadoLink(true)
      setTimeout(() => setCopiadoLink(false), 2500)
    } catch {
      toast.error(t('clientes.errorCopiar'))
    }
  }

  // Copia el acceso del cliente (link + correo, y la clave si se acaba de generar)
  const copiarCredenciales = async (c: Cliente) => {
    const pass = nuevasPass[c.id]
    let texto = `YUDA Importaciones: acceso a tu portal
${t('clientes.portalLink')}: ${portalUrl}
${t('clientes.email')}: ${c.email}`
    if (pass) texto += `\n${t('clientes.password')}: ${pass}`
    try {
      await navigator.clipboard.writeText(texto)
      toast.success(t('clientes.copiado'))
    } catch {
      toast.error(t('clientes.errorCopiar'))
    }
  }

  // Restablecer: como la contraseña actual no se puede ver (está encriptada),
  // genera una NUEVA y la revela en la ficha del cliente para reenviarla.
  const resetear = async (c: Cliente) => {
    if (!(await confirmar({ mensaje: t('clientes.confirmarReset', { nombre: c.nombre }) }))) return
    const nueva = generarPassword()
    try {
      await resetPasswordCliente(c.id, nueva)
      setNuevasPass((m) => ({ ...m, [c.id]: nueva }))
      toast.success(t('clientes.passwordReseteada'))
    } catch {
      toast.error(t('clientes.errorActualizar'))
    }
  }

  // Estado de cuenta oficial de Yuda Contable: PDF/imagen que se sube a
  // mano, sin ninguna conexión en vivo entre las dos apps.
  const [subiendoEstadoCuenta, setSubiendoEstadoCuenta] = useState(false)
  const subirEstadoCuenta = async (c: Cliente, archivo: File) => {
    setSubiendoEstadoCuenta(true)
    try {
      await subirEstadoCuentaOficial(c.id, archivo)
      toast.success(t('clientes.estadoCuentaSubido'))
      cargar()
    } catch {
      toast.error(t('clientes.errorEstadoCuenta'))
    } finally {
      setSubiendoEstadoCuenta(false)
    }
  }
  const [descargandoPdfContable, setDescargandoPdfContable] = useState(false)
  const descargarPdfContableStaff = async (c: Cliente) => {
    setDescargandoPdfContable(true)
    try {
      const blob = await descargarEstadoCuentaContablePdf(c.id)
      const url = URL.createObjectURL(blob)
      const enlace = document.createElement('a')
      enlace.href = url
      enlace.download = `estado_cuenta_${c.sigla || c.nombre}.pdf`
      enlace.click()
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch {
      toast.error(t('clientes.errorEstadoCuentaContable'))
    } finally {
      setDescargandoPdfContable(false)
    }
  }

  const quitarEstadoCuenta = async (c: Cliente) => {
    if (!(await confirmar({ mensaje: t('clientes.confirmarQuitarEstadoCuenta') }))) return
    try {
      await quitarEstadoCuentaOficial(c.id)
      toast.success(t('clientes.estadoCuentaQuitado'))
      cargar()
    } catch {
      toast.error(t('clientes.errorEstadoCuenta'))
    }
  }

  const vendedoras = equipo?.vendedoras ?? []
  const nombreVendedora: Record<string, string> = {}
  for (const v of vendedoras) nombreVendedora[v.user_id] = v.nombre

  // Cotizaciones esperando que Marcela cargue la naviera y el BL. Estaban en la
  // pagina "Equipo"; se traen aca, que es donde vive todo lo del cliente.
  const pendientesBl: { sesionId: string; numero: string; cliente: string; clienteId: string; vendedora: string }[] = []
  for (const v of vendedoras) {
    for (const c of v.clientes) {
      for (const cot of c.cotizaciones) {
        if (cot.pendiente_bl) {
          pendientesBl.push({
            sesionId: cot.sesion_id,
            numero: cot.numero,
            cliente: cot.nombre_cliente,
            clienteId: c.id,
            vendedora: v.nombre,
          })
        }
      }
    }
  }

  // Abre la ficha del cliente y despliega el seguimiento de esa cotizacion
  // Va directo a la pantalla de esa cotización puntual (ya no hace falta
  // pasar por el cliente y expandir algo ahí).
  const abrirPendiente = (_clienteId: string, sesionId: string) => {
    navigate(`/cotizacion/${sesionId}`)
  }

  const inactivos = clientes.filter((c) => !c.activo).length

  // Solo los que faltan por traer: mostrar los 44 con la mayoría marcados
  // "ya está" era puro ruido para Marcela, que solo necesita ver los nuevos.
  const pendientesImportar = previewContable.filter((p) => !p.ya_existe)

  const clienteAbierto = clientes.find((c) => c.id === clienteAbiertoId) ?? null

  // Si la URL ya trae un cliente (recién refrescada, o llegando por atrás/
  // adelante del navegador) pero la lista todavía no cargó, no hay que
  // mostrar la lista de golpe: solo espera.
  if (clienteAbiertoId && !clienteAbierto && cargandoClientes) {
    return (
      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.cargando')}</p>
    )
  }

  // Los importados de Yuda Contable que todavía nadie asignó a una vendedora
  // real van aparte: no son "tus clientes" todavía, son una lista de espera
  // para que Marcela decida a quién dárselos. Mezclarlos con los de verdad
  // era justo lo que hacía la pantalla ilegible.
  const clientesPendientes = clientes.filter((c) => c.pendiente_asignacion)

  const clientesFiltrados = (() => {
    const texto = busqueda.trim().toLowerCase()
    return clientes.filter((c) => {
      if (c.pendiente_asignacion) return false
      if (!c.activo && !verInactivos) return false
      if (filtroVendedora && c.vendedora_id !== filtroVendedora) return false
      if (!texto) return true
      return `${c.nombre} ${c.email} ${c.empresa ?? ''} ${c.pais ?? ''}`.toLowerCase().includes(texto)
    })
  })()

  // ---------- PANTALLA 2: la ficha de un cliente ----------
  if (clienteAbierto) {
    const c = clienteAbierto
    const cots = cotizaciones[c.id]
    return (
      <div className="flex flex-col gap-5">
        <button
          type="button"
          onClick={volverALista}
          className="flex items-center gap-2 self-start text-sm font-semibold"
          style={{ color: 'var(--yuda-primary)' }}
        >
          <ArrowLeft size={16} /> {t('clientes.volverALista')}
        </button>

        {/* Encabezado corto, siempre visible: quién es, para orientarse en
            cualquier pestaña sin tener que volver a leer todo de nuevo. */}
        <div className="flex items-center gap-3">
          <span
            className="flex flex-shrink-0 items-center justify-center font-bold"
            style={{ width: 44, height: 44, borderRadius: 999, fontSize: 18, backgroundColor: 'var(--yuda-primary)', color: 'var(--yuda-white)' }}
          >
            {(c.nombre || '?').trim().charAt(0).toUpperCase()}
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="truncate" style={{ fontWeight: 700, fontSize: 22, color: 'var(--yuda-accent)' }}>
              {c.nombre}
            </h1>
            <p className="truncate text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {[c.empresa, c.email, c.pais].filter(Boolean).join('  ')}
            </p>
          </div>
          <span
            className="flex-shrink-0 rounded-full px-3 py-1 text-xs font-semibold"
            style={
              c.activo
                ? { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
                : { backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }
            }
          >
            {c.activo ? t('clientes.activo') : t('clientes.inactivo')}
          </span>
        </div>

        {/* 3 pestañas: cada una responde una sola pregunta (quién es y qué
            hacer con él / cómo entra a su portal / qué cotizaciones tiene),
            en vez de mostrar las tres a la vez en una pantalla larga. */}
        <div className="flex gap-2 border-b" style={{ borderColor: 'var(--yuda-border)' }}>
          {(['cotizaciones', 'info', 'acceso'] as const).map((tabId) => (
            <button
              key={tabId}
              type="button"
              onClick={() => setTabCliente(tabId)}
              className="px-3 py-2 text-sm font-semibold"
              style={{
                color: tabCliente === tabId ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
                borderBottom: tabCliente === tabId ? '2px solid var(--yuda-primary)' : '2px solid transparent',
              }}
            >
              {t(`clientes.tab.${tabId}`)}
            </button>
          ))}
        </div>

        {/* Pestaña "Info": quién es y qué se puede hacer con él */}
        {tabCliente === 'info' && (
        <div className="card flex flex-col gap-4">
          {/* Datos básicos del cliente: antes esta pestaña no mostraba nada
              acá (solo lo de abajo, gran parte de eso exclusivo de admin), y
              para una vendedora se veía completamente vacía. */}
          <dl className="grid gap-2 border-b border-gray-100 pb-3 text-sm sm:grid-cols-[130px_1fr]">
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.email')}</dt>
            <dd className="break-all" style={{ color: 'var(--yuda-accent)' }}>{c.email}</dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.telefono')}</dt>
            <dd style={{ color: 'var(--yuda-accent)' }}>{c.telefono || '—'}</dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.pais')}</dt>
            <dd style={{ color: 'var(--yuda-accent)' }}>{c.pais || '—'}</dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.empresa')}</dt>
            <dd style={{ color: 'var(--yuda-accent)' }}>{c.empresa || '—'}</dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.nit')}</dt>
            <dd style={{ color: 'var(--yuda-accent)' }}>{c.nit || '—'}</dd>
          </dl>

          {esAdmin && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-medium" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('clientes.duenaLabel')}
              </span>
              {editandoDuena ? (
                <>
                  <select
                    value={duenaInput}
                    onChange={(e) => setDuenaInput(e.target.value)}
                    autoFocus
                    className="min-h-[38px] rounded-lg border border-gray-200 px-2 text-sm"
                    style={{ fontSize: 15 }}
                  >
                    <option value="">{t('clientes.duenaElegir')}</option>
                    {vendedoras.map((v) => (
                      <option key={v.user_id} value={v.user_id}>
                        {v.nombre}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => guardarDuena(c)}
                    disabled={!duenaInput || guardandoDuena}
                    className="rounded-lg px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: 'var(--yuda-primary)' }}
                  >
                    {t('common.guardar')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditandoDuena(false)}
                    className="text-sm"
                    style={{ color: 'var(--yuda-text-secondary)' }}
                  >
                    {t('common.cancelar')}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => {
                    setDuenaInput(c.vendedora_id)
                    setEditandoDuena(true)
                  }}
                  className="rounded-full px-3 py-1 text-sm font-semibold"
                  style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                >
                  {nombreVendedora[c.vendedora_id] || t('clientes.duenaSinResolver')}
                </button>
              )}
            </div>
          )}

          {/* Solo lectura a propósito: la sigla la controla Marcela desde Yuda
              Contable al crear el cliente ahí (así se marcan sus cajas de
              verdad). Se muestra a cualquier rol -no solo admin- porque la
              vendedora también necesita saber cómo llega marcada la caja. */}
          <div className="flex flex-wrap items-center gap-2 border-t border-gray-100 pt-3">
            <span className="text-sm font-medium" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('clientes.siglaLabel')}
            </span>
            <span
              className="rounded-full px-3 py-1 text-sm font-semibold"
              style={
                c.sigla
                  ? { backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }
                  : { backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }
              }
            >
              {c.sigla || t('clientes.siglaSinAsignar')}
            </span>
          </div>
          <p className="-mt-2 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.siglaAyuda')}
          </p>

          <div className="flex flex-wrap gap-2 border-t border-gray-100 pt-3">
            <button
              type="button"
              onClick={() => navigate(`/clientes/${c.id}/colaboracion`)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: 'var(--yuda-primary)' }}
            >
              <Users size={16} /> {t('clientes.verColaboracion')}
            </button>
            {puedeVerCuenta && (
              <button
                type="button"
                onClick={() => navigate(`/clientes/${c.id}/cuenta`)}
                className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
                style={{ color: 'var(--yuda-primary)' }}
              >
                <Wallet size={16} /> {t('cuentas.verCuenta')}
              </button>
            )}
            <button
              type="button"
              onClick={() => toggleActivo(c)}
              className="flex min-h-[42px] items-center rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: c.activo ? 'var(--yuda-error)' : 'var(--yuda-success)' }}
            >
              {c.activo ? t('clientes.desactivar') : t('clientes.activar')}
            </button>
            <button
              type="button"
              onClick={() => eliminar(c)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border px-4 text-sm font-semibold"
              style={{ borderColor: '#FCA5A5', color: 'var(--yuda-error)' }}
            >
              <Trash2 size={16} /> {t('clientes.eliminar')}
            </button>
          </div>
        </div>
        )}

        {/* Pestaña "Acceso": cómo entra este cliente a su portal */}
        {tabCliente === 'acceso' && (
        <>
        <div className="card flex flex-col gap-3">
          <h2 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            {t('clientes.accesoTitulo')}
          </h2>
          <dl className="grid gap-2 text-sm sm:grid-cols-[130px_1fr]">
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.portalLink')}</dt>
            <dd className="break-all">
              <a href={portalUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--yuda-primary)' }}>
                {portalUrl}
              </a>
            </dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.email')}</dt>
            <dd className="break-all" style={{ color: 'var(--yuda-accent)' }}>{c.email}</dd>
            <dt style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.password')}</dt>
            <dd>
              {nuevasPass[c.id] ? (
                <span style={{ fontFamily: 'monospace', color: 'var(--yuda-accent)' }}>{nuevasPass[c.id]}</span>
              ) : (
                <span style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.passwordOculta')}</span>
              )}
              {c.debe_cambiar_password && (
                <span
                  className="ml-2 rounded-full px-2 py-0.5 text-xs font-semibold"
                  style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}
                >
                  {t('clientes.claveSinCambiar')}
                </span>
              )}
            </dd>
          </dl>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => resetear(c)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: 'var(--yuda-primary)' }}
            >
              <KeyRound size={16} /> {t('clientes.resetPassword')}
            </button>
            <button
              type="button"
              onClick={() => copiarCredenciales(c)}
              className="flex min-h-[42px] items-center gap-2 rounded-lg border border-gray-200 px-4 text-sm font-semibold"
              style={{ color: 'var(--yuda-success)' }}
            >
              <Copy size={16} /> {t('clientes.copiar')}
            </button>
          </div>
        </div>

        {/* Estado de cuenta EN VIVO de Yuda Contable: solo si el cliente
            tiene sigla vinculada. Es el mismo PDF que genera esa app, al
            momento -no algo que Marcela suba a mano. */}
        {c.sigla && (
          <div className="card flex flex-col gap-3">
            <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
              <FileText size={18} /> {t('clientes.estadoCuentaContableTitulo')}
            </h2>
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('clientes.estadoCuentaContableAyuda')}
            </p>
            <button
              type="button"
              onClick={() => descargarPdfContableStaff(c)}
              disabled={descargandoPdfContable}
              className="flex w-fit items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: 'var(--yuda-primary)' }}
            >
              <FileText size={16} />
              {descargandoPdfContable ? t('clientes.subiendo') : t('clientes.descargarEstadoCuentaContable')}
            </button>
          </div>
        )}

        {/* Estado de cuenta oficial de Yuda Contable: documento puntual que
            Marcela sube a mano. Respaldo para clientes sin sigla (sin
            conexión en vivo posible). */}
        <div className="card flex flex-col gap-3">
          <h2 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            {t('clientes.estadoCuentaOficialTitulo')}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.estadoCuentaOficialAyuda')}
          </p>
          {c.estado_cuenta_oficial_url ? (
            <div className="flex flex-wrap items-center gap-3">
              <a
                href={c.estado_cuenta_oficial_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold"
                style={{ color: 'var(--yuda-primary)' }}
              >
                <FileText size={16} /> {t('clientes.verEstadoCuentaOficial')}
              </a>
              {c.estado_cuenta_oficial_actualizado_en && (
                <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                  {t('clientes.actualizadoEl', {
                    fecha: new Date(c.estado_cuenta_oficial_actualizado_en).toLocaleDateString('es-ES'),
                  })}
                </span>
              )}
              <button
                type="button"
                onClick={() => quitarEstadoCuenta(c)}
                className="flex items-center gap-1 text-sm font-semibold"
                style={{ color: 'var(--yuda-error)' }}
              >
                <X size={14} /> {t('clientes.quitar')}
              </button>
            </div>
          ) : (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('clientes.sinEstadoCuentaOficial')}
            </p>
          )}
          <label
            className="flex w-fit cursor-pointer items-center gap-2 rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold"
            style={{ color: subiendoEstadoCuenta ? 'var(--yuda-text-secondary)' : 'var(--yuda-primary)' }}
          >
            <FileText size={16} />
            {subiendoEstadoCuenta
              ? t('clientes.subiendo')
              : c.estado_cuenta_oficial_url
                ? t('clientes.reemplazarEstadoCuentaOficial')
                : t('clientes.subirEstadoCuentaOficial')}
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png,.webp"
              disabled={subiendoEstadoCuenta}
              className="hidden"
              onChange={(e) => {
                const archivo = e.target.files?.[0]
                e.target.value = ''
                if (archivo) subirEstadoCuenta(c, archivo)
              }}
            />
          </label>
        </div>
        </>
        )}

        {/* Pestaña "Cotizaciones" */}
        {tabCliente === 'cotizaciones' && (
        <div className="card flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
              {t('clientes.cotizacionesTitulo')}
            </h2>
            {!eligiendoTipoNueva && (
              <button
                type="button"
                onClick={() => setEligiendoTipoNueva(true)}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-semibold text-white"
                style={{ backgroundColor: 'var(--yuda-primary)' }}
              >
                <Plus size={16} /> {t('dashboard.nuevaCotizacion')}
              </button>
            )}
          </div>

          {/* Atajo: ya estamos en la ficha del cliente, así que lo único que
              falta decidir es qué se va a cotizar (cambia qué pide el OCR). */}
          {eligiendoTipoNueva && (
            <div className="flex flex-col gap-2 rounded-lg p-3" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
              <p className="text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                {t('dashboard.queCotizar')}
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <button
                  type="button"
                  onClick={() => iniciarNuevaCotizacion(c, 'productos')}
                  disabled={creandoTipoNueva !== null}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-primary)' }}
                >
                  <Package size={16} />
                  {creandoTipoNueva === 'productos' ? t('dashboard.creando') : t('dashboard.opcionProductos')}
                </button>
                <button
                  type="button"
                  onClick={() => iniciarNuevaCotizacion(c, 'bolsos')}
                  disabled={creandoTipoNueva !== null}
                  className="flex flex-1 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-primary)' }}
                >
                  <ShoppingBag size={16} />
                  {creandoTipoNueva === 'bolsos' ? t('dashboard.creando') : t('dashboard.opcionBolsos')}
                </button>
                <button
                  type="button"
                  onClick={() => setEligiendoTipoNueva(false)}
                  disabled={creandoTipoNueva !== null}
                  className="rounded-lg px-4 py-2 text-sm font-medium disabled:opacity-60"
                  style={{ color: 'var(--yuda-text-secondary)' }}
                >
                  {t('common.cancelar')}
                </button>
              </div>
            </div>
          )}

          {/* Mientras se elige qué cotizar para la nueva, la lista de abajo
              solo estorba: no hace falta volver a mostrarla acá. */}
          {!eligiendoTipoNueva && (cots === undefined ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('equipo.cargando')}</p>
          ) : cots.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.sinCotizaciones')}</p>
          ) : (
            <>
              {/* Por etapa: de un vistazo, sin abrir cada una para saber qué
                  le falta. El número en cada chip es cuántas hay ahí. */}
              <div className="flex flex-wrap gap-2">
                {(['todas', 'borrador', 'con_cliente', 'listas_bodega', 'en_bodega', 'en_camino', 'entregadas'] as const).map((et) => {
                  const cuantas = et === 'todas' ? cots.length : cots.filter((s) => etapaDeCotizacion(s) === et).length
                  if (et !== 'todas' && cuantas === 0) return null
                  const activo = subTabCot === et
                  return (
                    <button
                      key={et}
                      type="button"
                      onClick={() => setSubTabCot(et)}
                      className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold"
                      style={{
                        border: `1.5px solid ${activo ? 'var(--yuda-primary)' : 'var(--yuda-border)'}`,
                        backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'var(--yuda-white)',
                        color: activo ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
                      }}
                    >
                      {t(`clientes.etapa.${et}`)}
                      <span style={{ opacity: 0.7 }}>{cuantas}</span>
                    </button>
                  )
                })}
              </div>

              {/* Cada cotización abre en su propia pantalla ("/cotizacion/:id"):
                  nada se expande acá. Antes "Ver detalle" y "Gestionar
                  pedido" eran dos botones confusos que llevaban a cosas
                  distintas (uno navegaba, el otro expandía en el mismo
                  lugar) -ahora es un solo lugar para todo lo de esa
                  cotización, con sus propias pestañas adentro. */}
              <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
                {cots
                  .filter((s) => subTabCot === 'todas' || etapaDeCotizacion(s) === subTabCot)
                  .map((s) => {
                    const etapa = etapaDeCotizacion(s)
                    return (
                      <div key={s.id} className="flex w-full items-center gap-1 py-2 first:pt-0">
                        <button
                          type="button"
                          onClick={() => navigate(`/cotizacion/${s.id}`)}
                          className="flex min-w-0 flex-1 items-center justify-between gap-3 rounded-lg px-2 py-2 text-left transition-colors hover:bg-[var(--yuda-primary-soft)]"
                        >
                          <div className="min-w-0">
                            <p className="flex flex-wrap items-center gap-2">
                              <span style={{ fontWeight: 600, fontSize: 15, color: 'var(--yuda-accent)' }}>{numeroCot(s)}</span>
                              <PipelineEtapa etapa={etapa} />
                              <span
                                className="rounded-full px-2 py-0.5 text-xs font-semibold"
                                style={{ backgroundColor: COLOR_ETAPA[etapa].bg, color: COLOR_ETAPA[etapa].fg }}
                              >
                                {t(`clientes.etapa.${etapa}`)}
                              </span>
                            </p>
                            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{s.fecha}</p>
                          </div>
                          <ChevronRight size={18} style={{ color: 'var(--yuda-text-secondary)', flexShrink: 0 }} />
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation()
                            eliminarCotizacion(s, c.id)
                          }}
                          title={t('clientes.eliminarCotizacion')}
                          className="flex flex-shrink-0 items-center justify-center rounded-lg"
                          style={{ width: 44, height: 44, color: 'var(--yuda-error)' }}
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    )
                  })}
              </div>
            </>
          ))}
        </div>
        )}
      </div>
    )
  }

  // ---------- PANTALLA 1: la lista de clientes ----------
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>{t('clientes.titulo')}</h1>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.subtitulo')}
          </p>
        </div>
      </div>

      {/* Cómo se reparte el trabajo: quién crea el cliente y quién puede cotizarle.
          Se explica acá, en la cuenta de Marcela, porque ella es quien controla
          la asignación. */}
      {esAdmin && (
        <div className="rounded-xl border p-4 text-sm" style={{ borderColor: 'var(--yuda-border)', backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-text)' }}>
          <p style={{ fontWeight: 700, color: 'var(--yuda-accent)' }}>{t('clientes.reglaAsignacionTitulo')}</p>
          <p className="mt-1">{t('clientes.reglaAsignacionTexto')}</p>
        </div>
      )}

      {/* Lo que Marcela tiene que atender: cotizaciones esperando naviera y BL */}
      {esAdmin && pendientesBl.length > 0 && (
        <div className="rounded-xl border p-4" style={{ borderColor: '#FCD34D', backgroundColor: '#FFFBEB' }}>
          <p className="mb-2 flex items-center gap-2 text-sm font-bold" style={{ color: 'var(--yuda-warning-dark)' }}>
            <AlertCircle size={16} /> {t('equipo.pendientesBl', { n: pendientesBl.length })}
          </p>
          <div className="flex flex-col gap-1">
            {pendientesBl.map((p) => (
              <button
                key={p.sesionId}
                type="button"
                onClick={() => abrirPendiente(p.clienteId, p.sesionId)}
                className="flex flex-wrap items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-white"
                style={{ color: '#92400E' }}
              >
                <strong>{p.numero}</strong>
                <span>{p.cliente}</span>
                <span style={{ color: 'var(--yuda-warning-dark)' }}>({p.vendedora})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Estado de sincronización con Yuda Contable: todo, o un selector con
          lo que falta importar (nombre + sigla). No hay botón de crear
          cliente acá: todo cliente nace en Yuda Contable. */}
      {esAdmin && (
        <div className="card flex flex-col gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            <Users size={18} /> {t('clientes.sincronizacionTitulo')}
          </h2>
          {cargandoNoSincronizados ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('common.cargando')}</p>
          ) : noSincronizados === null ? (
            <p className="text-sm" style={{ color: 'var(--yuda-error)' }}>{t('clientes.errorBuscarContable')}</p>
          ) : noSincronizados.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--yuda-success)' }}>{t('clientes.todoSincronizado')}</p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('clientes.faltanSincronizar', { n: noSincronizados.length })}
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <select
                  value={siglaSeleccionadaSync}
                  onChange={(e) => setSiglaSeleccionadaSync(e.target.value)}
                  className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  style={{ fontSize: 16, minHeight: 44 }}
                >
                  <option value="">{t('clientes.elegirParaSincronizar')}</option>
                  {noSincronizados.map((r) => (
                    <option key={r.sigla} value={r.sigla}>
                      {(r.nombre || t('clientes.contableSinNombre')) + ' · ' + r.sigla}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => siglaSeleccionadaSync && importarUno(siglaSeleccionadaSync)}
                  disabled={!siglaSeleccionadaSync || importandoUno[siglaSeleccionadaSync]}
                  className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  style={{ backgroundColor: 'var(--yuda-primary)', minHeight: 44 }}
                >
                  {importandoUno[siglaSeleccionadaSync] ? t('clientes.importando') : t('clientes.importar')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Buscar EN VIVO en Yuda Contable: para un cliente puntual, sin
          esperar a que se regenere la lista fija de abajo. Solo admin. */}
      {esAdmin && (
        <div className="card flex flex-col gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            <Search size={18} /> {t('clientes.buscarContableTitulo')}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.buscarContableAyuda')}
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              value={busquedaContable}
              onChange={(e) => setBusquedaContable(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && buscarEnContable()}
              placeholder={t('clientes.buscarContablePlaceholder')}
              className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
              style={{ fontSize: 16 }}
            />
            <button
              type="button"
              onClick={buscarEnContable}
              disabled={busquedaContable.trim().length < 2 || buscandoContable}
              className="rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: 'var(--yuda-primary)' }}
            >
              {buscandoContable ? t('common.cargando') : t('historial.buscar')}
            </button>
          </div>
          {resultadosContable !== null && (
            resultadosContable.length === 0 ? (
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.buscarContableSinResultados')}</p>
            ) : (
              <div className="max-h-80 overflow-y-auto rounded-lg border" style={{ borderColor: 'var(--yuda-border)' }}>
                {resultadosContable.map((r) => (
                  <div
                    key={r.sigla}
                    className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
                    style={{ borderColor: 'var(--yuda-border)' }}
                  >
                    <span
                      className="rounded-full px-2 py-0.5 text-xs font-bold"
                      style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                    >
                      {r.sigla}
                    </span>
                    <span className="min-w-0 flex-1 truncate" style={{ color: 'var(--yuda-accent)' }}>
                      {r.nombre || t('clientes.contableSinNombre')}
                      {r.pais && <span style={{ color: 'var(--yuda-text-secondary)' }}> · {r.pais}</span>}
                    </span>
                    {r.ya_existe ? (
                      <span className="flex-shrink-0 text-xs font-semibold" style={{ color: 'var(--yuda-text-secondary)' }}>
                        {t('clientes.contableYaImportado')}
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => importarUno(r.sigla)}
                        disabled={importandoUno[r.sigla]}
                        className="flex-shrink-0 rounded-lg px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
                        style={{ backgroundColor: 'var(--yuda-primary)' }}
                      >
                        {importandoUno[r.sigla] ? t('clientes.importando') : t('clientes.importar')}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      )}

      {/* Importar clientes de Yuda Contable: trae los que ya existen allá y
          todavía no están acá. Solo admin. */}
      {esAdmin && (
        <div className="card">
          <button
            type="button"
            onClick={abrirImportar}
            className="flex w-full items-center justify-between text-left"
          >
            <span className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
              <UserPlus size={18} /> {t('clientes.importarContableTitulo')}
            </span>
            <ChevronDown
              size={18}
              style={{ transform: mostrarImportar ? 'rotate(180deg)' : 'none', color: 'var(--yuda-text-secondary)' }}
            />
          </button>
          {mostrarImportar && (
            <div className="mt-4 flex flex-col gap-3">
              <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('clientes.importarContableAyuda')}
              </p>
              {cargandoPreview ? (
                <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('common.cargando')}</p>
              ) : pendientesImportar.length === 0 ? (
                // Si ya se trajeron todos los que hay en Yuda Contable, no tiene
                // sentido mostrar una lista larga de "ya está" repetido 44 veces:
                // eso es justo el tipo de ruido que satura la pantalla.
                <p className="text-sm" style={{ color: 'var(--yuda-success)' }}>
                  {t('clientes.contableTodoImportado')}
                </p>
              ) : (
                <>
                  <div className="max-h-80 overflow-y-auto rounded-lg border" style={{ borderColor: 'var(--yuda-border)' }}>
                    {pendientesImportar.map((p) => (
                      <label
                        key={p.sigla}
                        className="flex items-center gap-3 border-b px-3 py-2 text-sm last:border-b-0"
                        style={{ borderColor: 'var(--yuda-border)' }}
                      >
                        <input
                          type="checkbox"
                          checked={siglasSeleccionadas.has(p.sigla)}
                          onChange={() => toggleSigla(p.sigla)}
                        />
                        <span
                          className="rounded-full px-2 py-0.5 text-xs font-bold"
                          style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                        >
                          {p.sigla}
                        </span>
                        <span className="min-w-0 flex-1 truncate" style={{ color: 'var(--yuda-accent)' }}>
                          {p.nombre || t('clientes.contableSinNombre')}
                          {p.pais && <span style={{ color: 'var(--yuda-text-secondary)' }}> · {p.pais}</span>}
                        </span>
                      </label>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={handleImportarContable}
                    disabled={siglasSeleccionadas.size === 0 || importando}
                    className="self-start rounded-lg px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
                    style={{ backgroundColor: 'var(--yuda-primary)' }}
                  >
                    {importando
                      ? t('clientes.importando')
                      : t('clientes.importarSeleccionados', { n: siglasSeleccionadas.size })}
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Importados de Yuda Contable sin asignar: aparte de "Tus clientes" a
          propósito -no son clientes de verdad todavía, es una lista de
          espera hasta que Marcela decida a qué vendedora dárselos. */}
      {esAdmin && clientesPendientes.length > 0 && (
        <div className="card flex flex-col gap-3" style={{ borderColor: 'var(--yuda-warning)', borderWidth: 1.5 }}>
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
            <UserPlus size={18} color="var(--yuda-warning-dark)" />
            {t('clientes.pendientesTitulo', { n: clientesPendientes.length })}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.pendientesAyuda')}
          </p>
          <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
            {clientesPendientes.map((c) => (
              <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <div className="min-w-0">
                  <p className="font-medium" style={{ color: 'var(--yuda-accent)' }}>{c.nombre}</p>
                  <p className="truncate text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {c.email}
                    {c.pais ? ` · ${c.pais}` : ''}
                  </p>
                </div>
                <select
                  disabled={asignandoPendiente[c.id]}
                  value=""
                  onChange={(e) => e.target.value && asignarPendiente(c.id, e.target.value)}
                  className="min-h-[36px] rounded-lg border px-2 text-sm focus:outline-none"
                  style={{ borderColor: 'var(--yuda-border)', color: 'var(--yuda-text)' }}
                >
                  <option value="">{t('clientes.asignarA')}</option>
                  {vendedoras.map((v) => (
                    <option key={v.user_id} value={v.user_id}>{v.nombre}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Lista de clientes */}
      <div className="card flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 18, color: 'var(--yuda-accent)' }}>
            <Users size={18} /> {t('clientes.listaTitulo')}
          </h2>
          {clientes.length >= 6 && (
            <div className="relative">
              <Search size={16} className="absolute" style={{ left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--yuda-text-secondary)' }} />
              <input
                type="text"
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
                placeholder={t('clientes.buscar')}
                style={{ ...inputStyle, paddingLeft: 36 }}
                className={inputClase}
              />
            </div>
          )}
        </div>

        {/* Los desactivados estan guardados, no borrados: se ven cuando se piden */}
        {inactivos > 0 && (
          <button
            type="button"
            onClick={() => setVerInactivos((v) => !v)}
            className="flex items-center gap-2 self-start text-sm font-semibold"
            style={{ color: 'var(--yuda-text-secondary)' }}
          >
            {verInactivos ? <EyeOff size={15} /> : <Eye size={15} />}
            {verInactivos
              ? t('clientes.ocultarInactivos')
              : t('clientes.verInactivos', { n: inactivos })}
          </button>
        )}

        {/* De quien es cada cliente. Reemplaza a la pagina "Equipo": la misma
            informacion, pero como filtro sobre una unica lista. */}
        {esAdmin && vendedoras.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {[{ id: '', nombre: t('clientes.todasLasVendedoras') }, ...vendedoras.map((v) => ({ id: v.user_id, nombre: v.nombre }))].map((v) => {
              const activo = filtroVendedora === v.id
              // Mismo criterio que clientesFiltrados: si no se está viendo
              // desactivados, no se cuentan -si no, el número del contador
              // no coincidía con cuántos aparecían realmente en la lista
              // (ej. "Sara Prueba 2" pero solo se veía 1 porque el otro
              // estaba desactivado).
              const cuantos = clientes.filter(
                (c) =>
                  !c.pendiente_asignacion &&
                  (c.activo || verInactivos) &&
                  (!v.id || c.vendedora_id === v.id),
              ).length
              return (
                <button
                  key={v.id || 'todas'}
                  type="button"
                  onClick={() => setFiltroVendedora(v.id)}
                  className="flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold"
                  style={{
                    border: `1.5px solid ${activo ? 'var(--yuda-primary)' : 'var(--yuda-border)'}`,
                    backgroundColor: activo ? 'var(--yuda-primary-soft)' : 'var(--yuda-white)',
                    color: activo ? 'var(--yuda-primary)' : 'var(--yuda-text-secondary)',
                  }}
                >
                  {v.nombre}
                  <span style={{ opacity: 0.7 }}>{cuantos}</span>
                </button>
              )
            })}
          </div>
        )}

        {cargandoClientes ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.cargando')}</p>
        ) : errorClientes ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm" style={{ color: 'var(--yuda-text)' }}>{t('clientes.errorCargar')}</p>
            <button
              type="button"
              onClick={cargar}
              className="flex items-center gap-2 rounded-lg px-4 font-semibold text-white"
              style={{ minHeight: 44, backgroundColor: 'var(--yuda-primary)', fontSize: 15 }}
            >
              <RefreshCw size={16} /> {t('clientes.reintentar')}
            </button>
          </div>
        ) : clientes.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.sinClientes')}
          </p>
        ) : clientesFiltrados.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('clientes.sinResultados', { texto: busqueda })}
          </p>
        ) : (
          <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
            {clientesFiltrados.map((c) => (
              <div key={c.id} className="flex w-full items-center gap-1 py-2 first:pt-0">
                <button
                  type="button"
                  onClick={() => abrirCliente(c)}
                  className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-1 py-1 text-left transition-colors hover:bg-[var(--yuda-primary-soft)]"
                >
                  <span
                    className="flex flex-shrink-0 items-center justify-center font-bold"
                    style={{ width: 38, height: 38, borderRadius: 999, fontSize: 15, backgroundColor: 'var(--yuda-primary)', color: 'var(--yuda-white)' }}
                  >
                    {(c.nombre || '?').trim().charAt(0).toUpperCase()}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate" style={{ fontWeight: 600, fontSize: 15, color: 'var(--yuda-accent)' }}>
                      {c.nombre}
                    </span>
                    <span className="block truncate text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {[c.empresa, c.email].filter(Boolean).join('  ')}
                    </span>
                    {esAdmin && nombreVendedora[c.vendedora_id] && (
                      <span className="mt-0.5 flex items-center gap-1 text-xs" style={{ color: 'var(--yuda-primary)' }}>
                        <UserRound size={12} /> {nombreVendedora[c.vendedora_id]}
                      </span>
                    )}
                  </span>
                  {!c.activo && (
                    <span
                      className="flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold"
                      style={{ backgroundColor: 'var(--yuda-error-soft)', color: 'var(--yuda-error)' }}
                    >
                      {t('clientes.inactivo')}
                    </span>
                  )}
                  <ChevronRight size={18} style={{ color: 'var(--yuda-text-secondary)', flexShrink: 0 }} />
                </button>
                {/* Borrar directo desde la lista: antes había que entrar a la
                    ficha del cliente solo para eliminarlo. Reusa `eliminar`,
                    que ya confirma y ofrece desactivar si tiene cotizaciones. */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    eliminar(c)
                  }}
                  aria-label={t('clientes.eliminar')}
                  title={t('clientes.eliminar')}
                  className="flex flex-shrink-0 items-center justify-center rounded-lg"
                  style={{ width: 44, height: 44, color: 'var(--yuda-error)' }}
                >
                  <Trash2 size={18} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Link del portal, al final: es informacion de referencia, no la tarea principal */}
      <div className="card flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--yuda-accent)' }}>{t('clientes.portalTitulo')}</p>
          <a href={portalUrl} target="_blank" rel="noreferrer" className="break-all text-sm" style={{ color: 'var(--yuda-primary)' }}>
            {portalUrl}
          </a>
          <p className="mt-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>{t('clientes.portalAyuda')}</p>
        </div>
        <button
          type="button"
          onClick={copiarLink}
          className="flex items-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium"
          style={{ color: 'var(--yuda-primary)' }}
        >
          {copiadoLink ? <Check size={16} /> : <Copy size={16} />} {copiadoLink ? t('clientes.copiado') : t('clientes.copiarLink')}
        </button>
      </div>
    </div>
  )
}

export default Clientes
