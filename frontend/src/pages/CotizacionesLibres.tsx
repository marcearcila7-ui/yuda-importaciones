import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import toast from 'react-hot-toast'
import { Trash2 } from 'lucide-react'
import { getSesiones, eliminarSesion } from '../api/packing'
import { getUsuarios } from '../api/admin'
import { confirmar } from '../store/confirmStore'
import { useAuthStore } from '../store/authStore'
import type { Sesion } from '../types/packing'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

// Cotizaciones sin cliente asociado ("libres"): no aparecen en Clientes (no
// tienen uno) ni tienen sentido mezcladas con el Historial de cotizaciones
// reales, así que viven en su propia pantalla para poder encontrarlas de
// nuevo más tarde.
function CotizacionesLibres() {
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const { usuario } = useAuthStore()
  const esAdmin = usuario?.rol === 'admin'

  const [sesiones, setSesiones] = useState<Sesion[]>([])
  const [nombresUsuarios, setNombresUsuarios] = useState<Record<string, string>>({})
  const [cargando, setCargando] = useState(true)
  const [eliminandoId, setEliminandoId] = useState<string | null>(null)

  useEffect(() => {
    setCargando(true)
    getSesiones()
      .then(setSesiones)
      .finally(() => setCargando(false))
    if (esAdmin) {
      getUsuarios()
        .then((usuarios) => {
          setNombresUsuarios(Object.fromEntries(usuarios.map((u) => [u.id, u.nombre])))
        })
        .catch(() => undefined)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const libres = sesiones
    .filter((s) => !s.cliente_id)
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))

  const handleEliminar = async (sesion: Sesion) => {
    const ok = await confirmar({
      mensaje: t('cotizacionesLibres.confirmarEliminar', { nombre: sesion.nombre_cliente }),
      peligro: true,
      textoConfirmar: t('cotizacionesLibres.eliminar'),
    })
    if (!ok) return
    setEliminandoId(sesion.id)
    try {
      await eliminarSesion(sesion.id)
      setSesiones((prev) => prev.filter((s) => s.id !== sesion.id))
      toast.success(t('cotizacionesLibres.eliminada'))
    } catch {
      toast.error(t('cotizacionesLibres.errorEliminar'))
    } finally {
      setEliminandoId(null)
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 style={{ fontWeight: 700, fontSize: 28, color: 'var(--yuda-accent)' }}>
          {t('cotizacionesLibres.titulo')}
        </h1>
        <p className="mt-1 text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('cotizacionesLibres.intro')}
        </p>
      </div>

      {cargando ? (
        <p style={{ color: 'var(--yuda-text-secondary)' }}>{t('cotizacionesLibres.cargando')}</p>
      ) : libres.length === 0 ? (
        <p className="mt-6 text-center" style={{ color: 'var(--yuda-text-secondary)' }}>
          {t('cotizacionesLibres.sinResultados')}
        </p>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full min-w-[560px] text-sm">
            <thead style={{ backgroundColor: 'var(--yuda-accent)', color: 'var(--yuda-white)' }}>
              <tr>
                <th className="px-4 py-3 text-left font-semibold">{t('cotizacionesLibres.fecha')}</th>
                <th className="px-4 py-3 text-left font-semibold">{t('cotizacionesLibres.nombre')}</th>
                {esAdmin && (
                  <th className="px-4 py-3 text-left font-semibold">{t('cotizacionesLibres.creadaPor')}</th>
                )}
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {libres.map((s, i) => (
                <tr key={s.id} style={{ backgroundColor: i % 2 === 0 ? 'var(--yuda-white)' : '#F9F9F7' }}>
                  <td className="px-4 py-3">
                    {new Date(s.fecha).toLocaleDateString(LOCALES[i18n.language] || 'es-ES')}
                  </td>
                  <td className="px-4 py-3 font-medium">{s.nombre_cliente}</td>
                  {esAdmin && (
                    <td className="px-4 py-3" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {nombresUsuarios[s.user_id] || '—'}
                    </td>
                  )}
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => navigate(`/cotizacion/${s.id}`)}
                        className="rounded-lg px-3 py-1 text-sm font-medium"
                        style={{ backgroundColor: 'var(--yuda-primary-soft)', color: 'var(--yuda-primary)' }}
                      >
                        {t('cotizacionesLibres.verDetalle')}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleEliminar(s)}
                        disabled={eliminandoId === s.id}
                        aria-label={t('cotizacionesLibres.eliminar')}
                        title={t('cotizacionesLibres.eliminar')}
                        className="flex items-center justify-center rounded-lg disabled:opacity-50"
                        style={{
                          width: 32,
                          height: 32,
                          backgroundColor: 'var(--yuda-error-soft)',
                          color: 'var(--yuda-error)',
                        }}
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default CotizacionesLibres
