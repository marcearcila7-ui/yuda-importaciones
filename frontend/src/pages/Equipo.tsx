import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertCircle, ChevronDown, ChevronRight, FileText, UserRound, Users } from 'lucide-react'
import SeguimientoEditor from '../components/SeguimientoEditor'
import { getEquipo } from '../api/admin'
import type { EquipoCotizacion, EquipoResponse } from '../types/equipo'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

function chipEstado(estado: string | null) {
  if (!estado) return { backgroundColor: '#F3F4F6', color: 'var(--yuda-text-secondary)' }
  if (estado === 'entregado') return { backgroundColor: 'var(--yuda-success-soft)', color: 'var(--yuda-success)' }
  return { backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }
}

function Equipo() {
  const { t, i18n } = useTranslation()
  const [equipo, setEquipo] = useState<EquipoResponse | null>(null)
  const [vendAbierta, setVendAbierta] = useState<Set<string>>(new Set())
  const [cliAbierto, setCliAbierto] = useState<Set<string>>(new Set())
  const [cotAbierta, setCotAbierta] = useState<Set<string>>(new Set())

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

  // Cotizaciones que esperan que Marcela cargue la naviera y el BL.
  const pendientes: { cot: EquipoCotizacion; vendedora: string }[] = []
  for (const v of equipo?.vendedoras ?? []) {
    for (const c of v.clientes) {
      for (const cot of c.cotizaciones) {
        if (cot.pendiente_bl) pendientes.push({ cot, vendedora: v.nombre })
      }
    }
  }

  const abrirPendiente = (sesionId: string) => {
    // Abre toda la jerarquía hasta esa cotización
    for (const v of equipo?.vendedoras ?? []) {
      for (const c of v.clientes) {
        if (c.cotizaciones.some((x) => x.sesion_id === sesionId)) {
          setVendAbierta((s) => new Set(s).add(v.user_id))
          setCliAbierto((s) => new Set(s).add(c.id))
          setCotAbierta((s) => new Set(s).add(sesionId))
        }
      }
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>{t('equipo.titulo')}</h1>
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('equipo.subtitulo')}
        </p>
      </div>

      {/* Pendientes de BL: lo que Marcela debe atender */}
      {pendientes.length > 0 && (
        <div className="rounded-xl border p-4" style={{ borderColor: '#FCD34D', backgroundColor: '#FFFBEB' }}>
          <p className="mb-2 flex items-center gap-2 text-sm font-bold" style={{ color: 'var(--yuda-warning-dark)' }}>
            <AlertCircle size={16} /> {t('equipo.pendientesBl', { n: pendientes.length })}
          </p>
          <div className="flex flex-col gap-1">
            {pendientes.map(({ cot, vendedora }) => (
              <button
                key={cot.sesion_id}
                type="button"
                onClick={() => abrirPendiente(cot.sesion_id)}
                className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-sm hover:bg-white"
              >
                <span style={{ color: '#92400E' }}>
                  <strong>{cot.numero}</strong> · {cot.nombre_cliente}
                  <span style={{ color: 'var(--yuda-warning-dark)' }}> ({vendedora})</span>
                </span>
                <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chipEstado(cot.estado)}>
                  {cot.estado ? t(`seguimiento.estados.${cot.estado}`) : ''}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {equipo === null ? (
        <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('equipo.cargando')}
        </p>
      ) : equipo.vendedoras.length === 0 ? (
        <div className="card">
          <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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
                    <span className="flex h-10 w-10 items-center justify-center rounded-full text-white" style={{ backgroundColor: 'var(--yuda-primary)' }}>
                      <Users size={18} />
                    </span>
                    <div>
                      <p className="font-semibold" style={{ color: 'var(--yuda-accent)' }}>{v.nombre}</p>
                      <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                        {t('equipo.clientesCount', { n: v.total_clientes })}
                      </p>
                    </div>
                  </div>
                  {abierta ? <ChevronDown size={20} style={{ color: 'var(--yuda-text-secondary)' }} /> : <ChevronRight size={20} style={{ color: 'var(--yuda-text-secondary)' }} />}
                </button>

                {/* Clientes de la vendedora */}
                {abierta && (
                  <div className="border-t border-gray-100 px-4 pb-4">
                    {v.clientes.length === 0 ? (
                      <p className="py-3 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
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
                                  <UserRound size={16} style={{ color: 'var(--yuda-primary)' }} />
                                  <span className="font-medium" style={{ color: 'var(--yuda-accent)' }}>
                                    {c.nombre}
                                  </span>
                                  {c.empresa && <span className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>· {c.empresa}</span>}
                                </div>
                                <span className="flex items-center gap-2 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                                  {c.cotizaciones.length}
                                  {cAbierto ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                                </span>
                              </button>

                              {/* Cotizaciones del cliente */}
                              {cAbierto && (
                                <div className="border-t border-gray-100 px-3 pb-3">
                                  {c.cotizaciones.length === 0 ? (
                                    <p className="py-2 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                                      {t('equipo.sinCotizaciones')}
                                    </p>
                                  ) : (
                                    <div className="flex flex-col gap-2 pt-2">
                                      {c.cotizaciones.map((cot) => {
                                        const coAbierta = cotAbierta.has(cot.sesion_id)
                                        return (
                                          <div key={cot.sesion_id} className="rounded-lg" style={{ backgroundColor: '#F9FAFB' }}>
                                            <button
                                              type="button"
                                              onClick={() => toggle(cotAbierta, setCotAbierta, cot.sesion_id)}
                                              className="flex w-full flex-wrap items-center justify-between gap-2 p-2 text-left"
                                            >
                                              <div className="flex min-w-0 items-center gap-2">
                                                <FileText size={15} className="flex-shrink-0" style={{ color: 'var(--yuda-text-secondary)' }} />
                                                <span className="truncate text-sm font-medium" style={{ color: 'var(--yuda-accent)' }}>
                                                  {cot.numero}
                                                </span>
                                                <span className="text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>{fmtFecha(cot.fecha)}</span>
                                              </div>
                                              <div className="flex items-center gap-2">
                                                {cot.pendiente_bl && (
                                                  <span className="flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold" style={{ backgroundColor: 'var(--yuda-warning-soft)', color: 'var(--yuda-warning-dark)' }}>
                                                    <AlertCircle size={12} /> {t('equipo.bl')}
                                                  </span>
                                                )}
                                                <span className="rounded-full px-2 py-0.5 text-xs font-semibold" style={chipEstado(cot.enviada ? cot.estado : null)}>
                                                  {cot.enviada && cot.estado
                                                    ? t(`seguimiento.estados.${cot.estado}`)
                                                    : t('equipo.noEnviada')}
                                                </span>
                                              </div>
                                            </button>

                                            {coAbierta && (
                                              <div className="border-t border-gray-100 p-3">
                                                {!cot.enviada ? (
                                                  <p className="text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                                                    {t('equipo.noEnviadaDetalle')}
                                                  </p>
                                                ) : (
                                                  <SeguimientoEditor sesionId={cot.sesion_id} />
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
