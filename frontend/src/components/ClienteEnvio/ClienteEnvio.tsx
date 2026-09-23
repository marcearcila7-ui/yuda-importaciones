import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Link as LinkIcon, Send, UserCheck } from 'lucide-react'
import { enviarACliente, getClientes, vincularCliente } from '../../api/clientes'
import SelectorCliente from '../SelectorCliente/SelectorCliente'
import type { Cliente } from '../../types/cliente'

interface Props {
  sesionId: string
  clienteIdInicial: string | null
  enviadaInicial: boolean
  nombreClienteSesion?: string
}

function ClienteEnvio({ sesionId, clienteIdInicial, enviadaInicial }: Props) {
  const { t } = useTranslation()
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [cargandoClientes, setCargandoClientes] = useState(true)
  const [errorClientes, setErrorClientes] = useState(false)
  const [clienteId, setClienteId] = useState<string | null>(clienteIdInicial)
  const [enviada, setEnviada] = useState(enviadaInicial)
  const [seleccion, setSeleccion] = useState('')
  const [trabajando, setTrabajando] = useState(false)

  // Antes esto fallaba en silencio total, igual que ya se corrigió en
  // SesionSelector: con mala señal el selector de cliente se quedaba vacío
  // para siempre sin avisar nada.
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
  }, [clienteIdInicial, enviadaInicial, sesionId])

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
      await enviarACliente(sesionId)
      setEnviada(true)
      toast.success(t('envio.enviada'))
    } catch {
      toast.error(t('envio.errorEnviar'))
    } finally {
      setTrabajando(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
        {t('envio.intro')}
      </p>

      {/* Asignar cliente ya existente. Ya no se puede crear uno acá: todo
          cliente nace en Yuda Contable y se importa desde la pantalla de
          Clientes. */}
      {!clienteActual ? (
        <div className="flex flex-col gap-3">
          {cargandoClientes ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('dashboard.cargandoClientes')}
            </p>
          ) : errorClientes ? (
            <div
              className="flex flex-col items-start gap-2 p-4"
              style={{ borderRadius: 12, backgroundColor: '#FEF2F2' }}
            >
              <p className="text-sm" style={{ color: 'var(--yuda-error-dark)' }}>
                {t('dashboard.errorCargarClientes')}
              </p>
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
              <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('envio.elegirCliente')}
              </span>
              <SelectorCliente clientes={clientes} valor={seleccion} onElegir={setSeleccion} />
              <button
                type="button"
                onClick={asignar}
                disabled={trabajando || !seleccion}
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
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl p-3" style={{ backgroundColor: 'var(--yuda-primary-soft)' }}>
          <div className="flex items-center gap-2">
            <UserCheck size={18} style={{ color: 'var(--yuda-primary)' }} />
            <span className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>
              {clienteActual.nombre}
            </span>
            <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {clienteActual.email}
            </span>
          </div>
          {!enviada && (
            <button type="button" onClick={desvincular} className="text-sm font-medium" style={{ color: 'var(--yuda-error)' }}>
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
          style={{ minHeight: 48, backgroundColor: 'var(--yuda-success)', borderRadius: 8, fontSize: 16 }}
        >
          <Send size={18} /> {t('envio.enviarBtn')}
        </button>
      )}

      {/* Ya enviada: el seguimiento se gestiona en Clientes */}
      {clienteActual && enviada && (
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
    </div>
  )
}

export default ClienteEnvio
