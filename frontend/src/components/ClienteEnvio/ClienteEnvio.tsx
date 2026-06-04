import { useEffect, useState } from 'react'
import type { CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Link as LinkIcon, Save, Send, Ship, UserCheck } from 'lucide-react'
import {
  enviarACliente,
  getClientes,
  getSeguimiento,
  guardarSeguimiento,
  vincularCliente,
} from '../../api/clientes'
import type { Cliente } from '../../types/cliente'
import { ESTADOS_ENVIO } from '../../types/seguimiento'
import type { Hito, Seguimiento } from '../../types/seguimiento'

interface Props {
  sesionId: string
  clienteIdInicial: string | null
  enviadaInicial: boolean
}

const inputStyle: CSSProperties = { fontSize: 16 }
const inputClase =
  'w-full rounded-lg border border-gray-200 px-3 py-2 min-h-[44px] focus:border-[#4B52E8] focus:outline-none'

function ClienteEnvio({ sesionId, clienteIdInicial, enviadaInicial }: Props) {
  const { t } = useTranslation()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [clienteId, setClienteId] = useState<string | null>(clienteIdInicial)
  const [enviada, setEnviada] = useState(enviadaInicial)
  const [seleccion, setSeleccion] = useState('')
  const [trabajando, setTrabajando] = useState(false)

  // Estado del seguimiento (editable)
  const [estado, setEstado] = useState<string>('cotizacion_enviada')
  const [novedades, setNovedades] = useState('')
  const [tracking, setTracking] = useState('')
  const [naviera, setNaviera] = useState('')
  const [urlTracking, setUrlTracking] = useState('')
  const [eta, setEta] = useState('')
  const [hitos, setHitos] = useState<Record<string, Hito>>({})

  useEffect(() => {
    getClientes()
      .then(setClientes)
      .catch(() => undefined)
  }, [])

  // Sincroniza con la cotización seleccionada
  useEffect(() => {
    setClienteId(clienteIdInicial)
    setEnviada(enviadaInicial)
  }, [clienteIdInicial, enviadaInicial, sesionId])

  const cargarSeguimiento = (s: Seguimiento) => {
    setEstado(s.estado)
    setNovedades(s.novedades ?? '')
    setTracking(s.numero_tracking ?? '')
    setNaviera(s.naviera ?? '')
    setUrlTracking(s.url_tracking ?? '')
    setEta(s.fecha_eta ?? '')
    setHitos(s.hitos ?? {})
  }

  useEffect(() => {
    if (!enviada) return
    getSeguimiento(sesionId).then((s) => {
      if (s) cargarSeguimiento(s)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enviada, sesionId])

  const clienteActual = clientes.find((c) => c.id === clienteId) || null

  const asignar = async () => {
    if (!seleccion) return
    setTrabajando(true)
    try {
      await vincularCliente(sesionId, seleccion)
      setClienteId(seleccion)
      toast.success(t('envio.clienteAsignado'))
    } catch {
      toast.error(t('envio.errorAsignar'))
    } finally {
      setTrabajando(false)
    }
  }

  const desvincular = async () => {
    setTrabajando(true)
    try {
      await vincularCliente(sesionId, null)
      setClienteId(null)
      setEnviada(false)
      setSeleccion('')
    } catch {
      toast.error(t('envio.errorAsignar'))
    } finally {
      setTrabajando(false)
    }
  }

  const enviar = async () => {
    setTrabajando(true)
    try {
      const s = await enviarACliente(sesionId)
      setEnviada(true)
      cargarSeguimiento(s)
      toast.success(t('envio.enviada'))
    } catch {
      toast.error(t('envio.errorEnviar'))
    } finally {
      setTrabajando(false)
    }
  }

  const setHito = (key: string, campo: keyof Hito, valor: string) =>
    setHitos((h) => ({ ...h, [key]: { ...h[key], [campo]: valor || null } }))

  const guardar = async () => {
    setTrabajando(true)
    // Solo enviar hitos que tengan fecha o nota
    const limpios: Record<string, Hito> = {}
    for (const k of ESTADOS_ENVIO) {
      const h = hitos[k]
      if (h && (h.fecha || h.nota)) limpios[k] = { fecha: h.fecha || null, nota: h.nota || null }
    }
    try {
      const s = await guardarSeguimiento(sesionId, {
        estado,
        novedades: novedades || null,
        numero_tracking: tracking || null,
        naviera: naviera || null,
        url_tracking: urlTracking || null,
        fecha_eta: eta || null,
        hitos: limpios,
      })
      cargarSeguimiento(s)
      toast.success(t('envio.seguimientoGuardado'))
    } catch {
      toast.error(t('envio.errorGuardar'))
    } finally {
      setTrabajando(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm" style={{ color: '#6B7280' }}>
        {t('envio.intro')}
      </p>

      {/* Asignar cliente */}
      {!clienteActual ? (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
          <label className="flex flex-1 flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
            {t('envio.elegirCliente')}
            <select
              value={seleccion}
              onChange={(e) => setSeleccion(e.target.value)}
              style={inputStyle}
              className={inputClase}
            >
              <option value="">{t('envio.selecciona')}</option>
              {clientes.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre} · {c.email}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={asignar}
            disabled={trabajando || !seleccion}
            className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
            style={{ minHeight: 44, backgroundColor: '#4B52E8', borderRadius: 8, padding: '0 18px', fontSize: 15 }}
          >
            <LinkIcon size={18} /> {t('envio.asignar')}
          </button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl p-3" style={{ backgroundColor: '#EEF0FD' }}>
          <div className="flex items-center gap-2">
            <UserCheck size={18} style={{ color: '#4B52E8' }} />
            <span className="font-semibold" style={{ color: '#0D0D0D' }}>
              {clienteActual.nombre}
            </span>
            <span className="text-sm" style={{ color: '#6B7280' }}>
              {clienteActual.email}
            </span>
          </div>
          {!enviada && (
            <button type="button" onClick={desvincular} className="text-sm font-medium" style={{ color: '#EF4444' }}>
              {t('envio.cambiar')}
            </button>
          )}
        </div>
      )}

      {/* Enviar al cliente */}
      {clienteActual && !enviada && (
        <button
          type="button"
          onClick={enviar}
          disabled={trabajando}
          className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
          style={{ minHeight: 48, backgroundColor: '#10B981', borderRadius: 8, fontSize: 16 }}
        >
          <Send size={18} /> {t('envio.enviarBtn')}
        </button>
      )}

      {/* Editor del seguimiento */}
      {clienteActual && enviada && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 rounded-lg p-2 text-sm" style={{ backgroundColor: '#D1FAE5', color: '#10B981' }}>
            <UserCheck size={16} /> {t('envio.yaEnviada')}
          </div>

          <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
            {t('envio.estadoActual')}
            <select value={estado} onChange={(e) => setEstado(e.target.value)} style={inputStyle} className={inputClase}>
              {ESTADOS_ENVIO.map((k) => (
                <option key={k} value={k}>
                  {t(`seguimiento.estados.${k}`)}
                </option>
              ))}
            </select>
          </label>

          {/* Datos de envío */}
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.numeroTracking')}
              <input value={tracking} onChange={(e) => setTracking(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.naviera')}
              <input value={naviera} onChange={(e) => setNaviera(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.urlTracking')}
              <input value={urlTracking} onChange={(e) => setUrlTracking(e.target.value)} placeholder="https://..." style={inputStyle} className={inputClase} />
            </label>
            <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
              {t('seguimiento.eta')}
              <input type="date" value={eta} onChange={(e) => setEta(e.target.value)} style={inputStyle} className={inputClase} />
            </label>
          </div>

          <label className="flex flex-col gap-1 text-sm" style={{ color: '#6B7280' }}>
            {t('seguimiento.novedades')}
            <textarea
              value={novedades}
              onChange={(e) => setNovedades(e.target.value)}
              rows={2}
              style={inputStyle}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 focus:border-[#4B52E8] focus:outline-none"
            />
          </label>

          {/* Fechas por hito */}
          <div>
            <p className="mb-2 flex items-center gap-2 text-sm font-semibold" style={{ color: '#0D0D0D' }}>
              <Ship size={16} /> {t('envio.fechasHitos')}
            </p>
            <div className="flex flex-col gap-2">
              {ESTADOS_ENVIO.map((k) => (
                <div key={k} className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_auto_2fr] sm:items-center">
                  <span className="text-sm" style={{ color: '#374151' }}>
                    {t(`seguimiento.estados.${k}`)}
                  </span>
                  <input
                    type="date"
                    value={hitos[k]?.fecha ?? ''}
                    onChange={(e) => setHito(k, 'fecha', e.target.value)}
                    style={inputStyle}
                    className="rounded-lg border border-gray-200 px-2 py-1 focus:border-[#4B52E8] focus:outline-none"
                  />
                  <input
                    value={hitos[k]?.nota ?? ''}
                    onChange={(e) => setHito(k, 'nota', e.target.value)}
                    placeholder={t('seguimiento.notaOpcional')}
                    style={inputStyle}
                    className="rounded-lg border border-gray-200 px-2 py-1 focus:border-[#4B52E8] focus:outline-none"
                  />
                </div>
              ))}
            </div>
          </div>

          <button
            type="button"
            onClick={guardar}
            disabled={trabajando}
            className="flex items-center justify-center gap-2 font-semibold text-white disabled:opacity-60"
            style={{ minHeight: 48, backgroundColor: '#4B52E8', borderRadius: 8, fontSize: 16 }}
          >
            <Save size={18} /> {t('envio.guardarSeguimiento')}
          </button>
        </div>
      )}
    </div>
  )
}

export default ClienteEnvio
