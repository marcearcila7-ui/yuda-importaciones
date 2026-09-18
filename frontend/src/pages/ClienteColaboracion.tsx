import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { ArrowLeft, FileText, MessageSquare, Send, UserPlus, Users, X } from 'lucide-react'
import {
  agregarActividadCliente,
  asignarVendedorasCliente,
  getCliente,
  getColaboracionCliente,
  quitarVendedoraCliente,
} from '../api/clientes'
import { getEquipo } from '../api/admin'
import { useAuthStore } from '../store/authStore'
import type { Cliente, ClienteColaboracion as ClienteColaboracionType } from '../types/cliente'
import type { EquipoVendedora } from '../types/equipo'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

function ClienteColaboracion() {
  const { clienteId } = useParams<{ clienteId: string }>()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const esAdmin = useAuthStore((s) => s.usuario?.rol) === 'admin'
  const locale = LOCALES[i18n.language] || 'es-ES'

  const [cliente, setCliente] = useState<Cliente | null>(null)
  const [datos, setDatos] = useState<ClienteColaboracionType | null>(null)
  const [vendedoras, setVendedoras] = useState<EquipoVendedora[]>([])
  const [cargando, setCargando] = useState(true)
  const [vendedoraElegida, setVendedoraElegida] = useState('')
  const [asignando, setAsignando] = useState(false)
  const [nota, setNota] = useState('')
  const [guardandoNota, setGuardandoNota] = useState(false)

  const cargar = useCallback(() => {
    if (!clienteId) return
    setCargando(true)
    Promise.all([getCliente(clienteId), getColaboracionCliente(clienteId)])
      .then(([c, colab]) => {
        setCliente(c)
        setDatos(colab)
      })
      .catch(() => toast.error(t('colaboracion.errorCargar')))
      .finally(() => setCargando(false))
  }, [clienteId, t])

  useEffect(() => {
    cargar()
  }, [cargar])

  useEffect(() => {
    if (!esAdmin) return
    getEquipo()
      .then((r) => setVendedoras(r.vendedoras))
      .catch(() => setVendedoras([]))
  }, [esAdmin])

  const fmtFecha = (iso: string) =>
    new Date(iso).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })

  const yaAsignadas = new Set([
    ...(datos ? [datos.duena.id] : []),
    ...(datos?.asignadas.map((a) => a.vendedora.id) ?? []),
  ])
  const opcionesVendedora = vendedoras.filter((v) => !yaAsignadas.has(v.user_id))

  const asignar = async () => {
    if (!clienteId || !vendedoraElegida) return
    setAsignando(true)
    try {
      await asignarVendedorasCliente(clienteId, [vendedoraElegida])
      setVendedoraElegida('')
      toast.success(t('colaboracion.vendedoraAgregada'))
      cargar()
    } catch {
      toast.error(t('colaboracion.errorAsignar'))
    } finally {
      setAsignando(false)
    }
  }

  const quitar = async (vendedoraId: string) => {
    if (!clienteId) return
    try {
      await quitarVendedoraCliente(clienteId, vendedoraId)
      toast.success(t('colaboracion.vendedoraQuitada'))
      cargar()
    } catch {
      toast.error(t('colaboracion.errorQuitar'))
    }
  }

  const agregarNota = async () => {
    if (!clienteId || !nota.trim()) return
    setGuardandoNota(true)
    try {
      await agregarActividadCliente(clienteId, nota.trim())
      setNota('')
      toast.success(t('colaboracion.notaAgregada'))
      cargar()
    } catch {
      toast.error(t('colaboracion.errorNota'))
    } finally {
      setGuardandoNota(false)
    }
  }

  if (cargando) {
    return (
      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
        {t('common.cargando')}
      </p>
    )
  }

  if (!cliente || !datos) {
    return (
      <div className="card">
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('colaboracion.errorCargar')}
        </p>
      </div>
    )
  }

  return (
    <>
      <button
        type="button"
        onClick={() => navigate('/clientes')}
        className="mb-4 flex items-center gap-1 text-sm font-medium"
        style={{ color: 'var(--yuda-primary)' }}
      >
        <ArrowLeft size={16} /> {t('common.volver')}
      </button>

      <div className="flex flex-col gap-6">
        <div>
          <h1 style={{ fontWeight: 700, fontSize: 24, color: 'var(--yuda-accent)' }}>{cliente.nombre}</h1>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>{cliente.email}</p>
        </div>

        {/* Vendedoras que gestionan este cliente */}
        <div className="card flex flex-col gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            <Users size={18} /> {t('colaboracion.vendedorasTitulo')}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('colaboracion.vendedorasAyuda')}
          </p>
          <div className="flex flex-wrap gap-2">
            <span
              className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold"
              style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
            >
              {datos.duena.nombre} · {t('colaboracion.duena')}
            </span>
            {datos.asignadas.map((a) => (
              <span
                key={a.vendedora.id}
                className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-semibold"
                style={{ backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success-dark)' }}
              >
                {a.vendedora.nombre}
                {esAdmin && (
                  <button
                    type="button"
                    onClick={() => quitar(a.vendedora.id)}
                    aria-label={t('colaboracion.quitar')}
                    style={{ color: 'var(--yuda-success-dark)' }}
                  >
                    <X size={14} />
                  </button>
                )}
              </span>
            ))}
          </div>

          {esAdmin && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select
                value={vendedoraElegida}
                onChange={(e) => setVendedoraElegida(e.target.value)}
                className="min-h-[42px] rounded-lg border border-gray-200 px-3 text-sm"
                style={{ fontSize: 15 }}
              >
                <option value="">{t('colaboracion.seleccionarVendedora')}</option>
                {opcionesVendedora.map((v) => (
                  <option key={v.user_id} value={v.user_id}>
                    {v.nombre}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={asignar}
                disabled={!vendedoraElegida || asignando}
                className="flex min-h-[42px] items-center gap-2 rounded-lg px-4 text-sm font-semibold text-white disabled:opacity-60"
                style={{ backgroundColor: 'var(--yuda-primary)' }}
              >
                <UserPlus size={16} /> {t('colaboracion.agregarVendedora')}
              </button>
            </div>
          )}
        </div>

        {/* Todas las cotizaciones del cliente, de cualquier vendedora */}
        <div className="card flex flex-col gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            <FileText size={18} /> {t('colaboracion.cotizacionesTitulo')}
          </h2>
          {datos.cotizaciones.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('colaboracion.sinCotizaciones')}
            </p>
          ) : (
            <div className="flex flex-col divide-y" style={{ borderColor: 'var(--yuda-border)' }}>
              {datos.cotizaciones.map((c) => (
                <Link
                  key={c.sesion_id}
                  to={`/cotizacion/${c.sesion_id}`}
                  className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm hover:opacity-80"
                >
                  <span style={{ color: 'var(--yuda-accent)' }}>
                    <span className="font-semibold">{c.numero}</span> · {fmtFecha(c.fecha)}
                  </span>
                  <span className="flex items-center gap-2">
                    <span
                      className="rounded-full px-2.5 py-0.5 text-xs font-semibold"
                      style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                    >
                      {c.vendedora_nombre}
                    </span>
                    {c.estado_envio && (
                      <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                        {t(`seguimiento.estados.${c.estado_envio}`)}
                      </span>
                    )}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Bitácora de actividad */}
        <div className="card flex flex-col gap-3">
          <h2 className="flex items-center gap-2" style={{ fontWeight: 700, fontSize: 16, color: 'var(--yuda-accent)' }}>
            <MessageSquare size={18} /> {t('colaboracion.actividadTitulo')}
          </h2>
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
            {t('colaboracion.actividadAyuda')}
          </p>

          <div className="flex gap-2">
            <input
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && agregarNota()}
              placeholder={t('colaboracion.notaPlaceholder')}
              className="min-h-[44px] flex-1 rounded-lg border border-gray-200 px-3"
              style={{ fontSize: 16 }}
            />
            <button
              type="button"
              onClick={agregarNota}
              disabled={!nota.trim() || guardandoNota}
              className="flex min-h-[44px] items-center gap-2 rounded-lg px-4 text-sm font-semibold text-white disabled:opacity-60"
              style={{ backgroundColor: 'var(--yuda-primary)' }}
            >
              <Send size={16} />
            </button>
          </div>

          {datos.actividad.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
              {t('colaboracion.sinActividad')}
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {datos.actividad.map((a) => (
                <div key={a.id} className="rounded-lg px-3 py-2" style={{ backgroundColor: '#F9FAFB' }}>
                  <p className="text-sm" style={{ color: 'var(--yuda-text)' }}>{a.nota}</p>
                  <p className="mt-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                    {a.usuario_nombre} ·{' '}
                    {new Date(a.created_at).toLocaleString(locale, {
                      day: 'numeric',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

export default ClienteColaboracion
