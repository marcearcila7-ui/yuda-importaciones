import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronRight, FileText, UserRound, Users } from 'lucide-react'
import SeguimientoTimeline from '../components/portal/SeguimientoTimeline'
import { getEquipo } from '../api/admin'
import { getSeguimiento } from '../api/clientes'
import type { EquipoCotizacion, EquipoResponse } from '../types/equipo'
import type { Seguimiento } from '../types/seguimiento'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

function chipEstado(estado: string | null) {
  if (!estado) return { backgroundColor: '#F3F4F6', color: '#9CA3AF' }
  if (estado === 'entregado') return { backgroundColor: '#D1FAE5', color: '#10B981' }
  return { backgroundColor: '#EEF0FD', color: '#4B52E8' }
}

function Equipo() {
  const { t, i18n } = useTranslation()
  const [equipo, setEquipo] = useState<EquipoResponse | null>(null)
  const [vendAbierta, setVendAbierta] = useState<Set<string>>(new Set())
  const [cliAbierto, setCliAbierto] = useState<Set<string>>(new Set())
  const [cotAbierta, setCotAbierta] = useState<Set<string>>(new Set())
  // sesion_id -> seguimiento | 'loading' | null (sin datos)
  const [seguimientos, setSeguimientos] = useState<Record<string, Seguimiento | 'loading' | null>>({})

  useEffect(() => {
    getEquipo()
      .then(setEquipo)
      .catch(() => setEquipo({ vendedoras: [] }))
  }, [])

  const toggle = (set: Set<string>, fn: (s: Set<string>) => void, id: string) => {
    const copia = new Set(set)
    copia.has(id) ? copia.delete(id) : copia.add(id)
    fn(copia)
  }

  const fmtFecha = (s: string) => {
    const [y, m, d] = s.split('-').map(Number)
    if (!y || !m || !d) return s
    return new Date(y, m - 1, d).toLocaleDateString(LOCALES[i18n.language] || 'es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  const abrirCotizacion = (cot: EquipoCotizacion) => {
    toggle(cotAbierta, setCotAbierta, cot.sesion_id)
    if (cot.enviada && seguimientos[cot.sesion_id] === undefined) {
      setSeguimientos((s) => ({ ...s, [cot.sesion_id]: 'loading' }))
      getSeguimiento(cot.sesion_id).then((seg) =>
        setSeguimientos((s) => ({ ...s, [cot.sesion_id]: seg })),
      )
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: '#0D0D0D' }}>{t('equipo.titulo')}</h1>
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {t('equipo.subtitulo')}
        </p>
      </div>

      {equipo === null ? (
        <p className="text-sm" style={{ color: '#6B7280' }}>
          {t('equipo.cargando')}
        </p>
      ) : equipo.vendedoras.length === 0 ? (
        <div className="card">
          <p className="text-sm" style={{ color: '#6B7280' }}>
            {t('equipo.sinVendedoras')}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {equipo.vendedoras.map((v) => {
            const abierta = vendAbierta.has(v.user_id)
            return (
              <div key={v.user_id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
                {/* Vendedora */}
                <button
                  type="button"
                  onClick={() => toggle(vendAbierta, setVendAbierta, v.user_id)}
                  className="flex w-full items-center justify-between gap-3 p-4 text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full text-white" style={{ backgroundColor: '#4B52E8' }}>
                      <Users size={18} />
                    </span>
                    <div>
                      <p className="font-semibold" style={{ color: '#0D0D0D' }}>{v.nombre}</p>
                      <p className="text-sm" style={{ color: '#6B7280' }}>
                        {t('equipo.clientesCount', { n: v.total_clientes })}
                      </p>
                    </div>
                  </div>
                  {abierta ? <ChevronDown size={20} style={{ color: '#9CA3AF' }} /> : <ChevronRight size={20} style={{ color: '#9CA3AF' }} />}
                </button>

                {/* Clientes de la vendedora */}
                {abierta && (
                  <div className="border-t border-gray-100 px-4 pb-4">
                    {v.clientes.length === 0 ? (
                      <p className="py-3 text-sm" style={{ color: '#9CA3AF' }}>
                        {t('equipo.sinClientes')}
                      </p>
                    ) : (
                      <div className="flex flex-col gap-2 pt-3">
                        {v.clientes.map((c) => {
                          const cAbierto = cliAbierto.has(c.id)
                          return (
                            <div key={c.id} className="rounded-xl border border-gray-200">
                              <button
                                type="button"
                                onClick={() => toggle(cliAbierto, setCliAbierto, c.id)}
                                className="flex w-full items-center justify-between gap-3 p-3 text-left"
                              >
                                <div className="flex items-center gap-2">
                                  <UserRound size={16} style={{ color: '#4B52E8' }} />
                                  <span className="font-medium" style={{ color: '#0D0D0D' }}>
                                    {c.nombre}
                                  </span>
                                  {c.empresa && <span className="text-sm" style={{ color: '#9CA3AF' }}>· {c.empresa}</span>}
                                </div>
                                <span className="flex items-center gap-2 text-sm" style={{ color: '#6B7280' }}>
                                  {c.cotizaciones.length}
                                  {cAbierto ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                </span>
                              </button>

                              {/* Cotizaciones del cliente */}
                              {cAbierto && (
                                <div className="border-t border-gray-100 px-3 pb-3">
                                  {c.cotizaciones.length === 0 ? (
                                    <p className="py-2 text-sm" style={{ color: '#9CA3AF' }}>
                                      {t('equipo.sinCotizaciones')}
                                    </p>
                                  ) : (
                                    <div className="flex flex-col gap-2 pt-2">
                                      {c.cotizaciones.map((cot) => {
                                        const coAbierta = cotAbierta.has(cot.sesion_id)
                                        const seg = seguimientos[cot.sesion_id]
                                        return (
                                          <div key={cot.sesion_id} className="rounded-lg" style={{ backgroundColor: '#F9FAFB' }}>
                                            <button
                                              type="button"
                                              onClick={() => abrirCotizacion(cot)}
                                              className="flex w-full items-center justify-between gap-2 p-2 text-left"
                                            >
                                              <div className="flex items-center gap-2">
                                                <FileText size={15} style={{ color: '#6B7280' }} />
                                                <span className="text-sm font-medium" style={{ color: '#0D0D0D' }}>
                                                  {cot.numero}
                                                </span>
                                                <span className="text-xs" style={{ color: '#9CA3AF' }}>{fmtFecha(cot.fecha)}</span>
                                              </div>
                                              <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chipEstado(cot.enviada ? cot.estado : null)}>
                                                {cot.enviada && cot.estado
                                                  ? t(`seguimiento.estados.${cot.estado}`)
                                                  : t('equipo.noEnviada')}
                                              </span>
                                            </button>

                                            {coAbierta && (
                                              <div className="border-t border-gray-100 p-3">
                                                {!cot.enviada ? (
                                                  <p className="text-sm" style={{ color: '#9CA3AF' }}>
                                                    {t('equipo.noEnviadaDetalle')}
                                                  </p>
                                                ) : seg === 'loading' || seg === undefined ? (
                                                  <p className="text-sm" style={{ color: '#9CA3AF' }}>
                                                    {t('equipo.cargandoSeguimiento')}
                                                  </p>
                                                ) : seg ? (
                                                  <SeguimientoTimeline seguimiento={seg} />
                                                ) : (
                                                  <p className="text-sm" style={{ color: '#9CA3AF' }}>
                                                    {t('equipo.cargandoSeguimiento')}
                                                  </p>
                                                )}
                                              </div>
                                            )}
                                          </div>
                                        )
                                      })}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default Equipo
