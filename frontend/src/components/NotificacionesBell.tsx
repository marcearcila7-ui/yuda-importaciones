import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Bell, Check, Trash2 } from 'lucide-react'
import {
  eliminarNotificacion,
  eliminarTodasNotificaciones,
  getNotificaciones,
  marcarLeida,
  marcarTodasLeidas,
} from '../api/notificaciones'
import type { Notificacion } from '../types/notificacion'
import { confirmar } from '../store/confirmStore'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

// A qué pestaña de /cotizacion/:id llevar según qué está avisando el sistema
// -así el clic entra directo a lo que la notificación describe, en vez de
// dejar a quien la lee adivinando dónde mirar.
const TAB_POR_TIPO: Record<string, string> = {
  cubicaje_bodega: 'cubicaje',
  bodega_envio_a_vendedora: 'seguimiento',
  despacho_aprobado: 'seguimiento',
  envio_vendedora: 'seguimiento',
  listo_para_envio: 'seguimiento',
  inspeccion_bodega_actualizada: 'gestion',
  orden_actualizada_bodega: 'gestion',
  pedido_regenerado_tras_revision: 'gestion',
  pedido_cliente: 'gestion',
  pedido_confirmado: 'gestion',
}

// Campana de avisos para Marcela: muestra las cotizaciones listas para cargar BL.
// Refresca cada 8s para que un aviso de bodega (ej. cubicaje) le llegue casi
// al instante, sin tener que recargar la página.
// posicion: hacia dónde abre el panel. 'arriba' (sidebar de escritorio) o
// 'abajo' (TopBar móvil).
function NotificacionesBell({ posicion = 'arriba' }: { posicion?: 'arriba' | 'abajo' }) {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [items, setItems] = useState<Notificacion[]>([])
  const [abierto, setAbierto] = useState(false)
  const cajaRef = useRef<HTMLDivElement>(null)

  const cargar = () => {
    getNotificaciones().then(setItems).catch(() => {})
  }

  useEffect(() => {
    cargar()
    const id = setInterval(cargar, 8000)
    // En el celular, el navegador congela los timers cuando la pantalla se
    // apaga o se cambia de app: al volver, esto refresca de una vez en vez
    // de esperar hasta 8s (o quedarse pegado si el intervalo se perdió).
    const onVisible = () => {
      if (document.visibilityState === 'visible') cargar()
    }
    document.addEventListener('visibilitychange', onVisible)
    window.addEventListener('focus', onVisible)
    return () => {
      clearInterval(id)
      document.removeEventListener('visibilitychange', onVisible)
      window.removeEventListener('focus', onVisible)
    }
  }, [])

  // Cierra el panel al hacer clic fuera
  useEffect(() => {
    if (!abierto) return
    const onClick = (e: MouseEvent) => {
      if (cajaRef.current && !cajaRef.current.contains(e.target as Node)) setAbierto(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [abierto])

  const noLeidas = items.filter((n) => !n.leida).length
  const locale = LOCALES[i18n.language] || 'es-ES'

  // Al tocar un aviso: lo marca leído y lleva directo a la pestaña de la
  // cotización que describe (según el tipo de aviso), no solo a la ficha en
  // general -así no hay que adivinar dónde mirar.
  const leerUna = async (n: Notificacion) => {
    setAbierto(false)
    if (!n.leida) {
      setItems((xs) => xs.map((x) => (x.id === n.id ? { ...x, leida: true } : x)))
      marcarLeida(n.id).catch(() => cargar())
    }
    if (n.sesion_id) {
      const tab = TAB_POR_TIPO[n.tipo]
      navigate(`/cotizacion/${n.sesion_id}`, tab ? { state: { tab } } : undefined)
    }
  }

  const leerTodas = async () => {
    setItems((xs) => xs.map((x) => ({ ...x, leida: true })))
    try {
      await marcarTodasLeidas()
    } catch {
      cargar()
    }
  }

  const eliminarUna = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setItems((xs) => xs.filter((x) => x.id !== id))
    eliminarNotificacion(id).catch(() => cargar())
  }

  const eliminarTodas = async () => {
    const ok = await confirmar({ mensaje: t('notif.confirmarEliminarTodas'), peligro: true })
    if (!ok) return
    setItems([])
    eliminarTodasNotificaciones().catch(() => cargar())
  }

  return (
    <div className="relative" ref={cajaRef}>
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        className="relative flex h-11 w-11 items-center justify-center rounded-full"
        style={{ backgroundColor: '#F3F4F6', color: 'var(--yuda-text)' }}
        aria-label={t('notif.titulo')}
      >
        <Bell size={18} />
        {noLeidas > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full px-1 text-xs font-bold text-white"
            style={{ backgroundColor: 'var(--yuda-error)' }}
          >
            {noLeidas > 9 ? '9+' : noLeidas}
          </span>
        )}
      </button>

      {abierto && (
        <div
          // En el TopBar móvil ("abajo") la campana no está pegada al borde
          // derecho de la pantalla, así que "absolute right-0" abría el
          // panel relativo al propio ícono y se salía de la pantalla por la
          // izquierda. "fixed" + posición respecto a la pantalla lo evita.
          className={`z-50 w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl bg-white ${
            posicion === 'abajo' ? 'fixed right-4 top-14' : 'absolute bottom-12 left-0'
          }`}
          style={{ boxShadow: '0 10px 30px rgba(0,0,0,0.25)' }}
        >
          <div className="flex items-center justify-between gap-3 border-b border-gray-100 px-4 py-3">
            <p className="text-sm font-bold" style={{ color: 'var(--yuda-accent)' }}>
              {t('notif.titulo')}
            </p>
            <div className="flex items-center gap-3">
              {noLeidas > 0 && (
                <button
                  type="button"
                  onClick={leerTodas}
                  className="flex items-center gap-1 text-xs font-medium"
                  style={{ color: 'var(--yuda-primary)' }}
                >
                  <Check size={14} /> {t('notif.marcarTodas')}
                </button>
              )}
              {items.length > 0 && (
                <button
                  type="button"
                  onClick={eliminarTodas}
                  className="flex items-center gap-1 text-xs font-medium"
                  style={{ color: 'var(--yuda-text-secondary)' }}
                >
                  <Trash2 size={14} /> {t('notif.eliminarTodas')}
                </button>
              )}
            </div>
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm" style={{ color: 'var(--yuda-text-secondary)' }}>
                {t('notif.sinAvisos')}
              </p>
            ) : (
              items.map((n) => (
                <div
                  key={n.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => leerUna(n)}
                  onKeyDown={(e) => e.key === 'Enter' && leerUna(n)}
                  className="flex w-full cursor-pointer items-start gap-2 border-b border-gray-50 px-4 py-3 text-left"
                  style={{ backgroundColor: n.leida ? 'var(--yuda-white)' : 'var(--yuda-primary-soft)' }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      {!n.leida && (
                        <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ backgroundColor: 'var(--yuda-primary)' }} />
                      )}
                      <span className="text-sm font-semibold" style={{ color: 'var(--yuda-accent)' }}>
                        {n.titulo}
                      </span>
                    </div>
                    {n.mensaje && (
                      <p className="mt-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                        {n.mensaje}
                      </p>
                    )}
                    <p className="mt-1 text-xs" style={{ color: 'var(--yuda-text-secondary)' }}>
                      {new Date(n.created_at).toLocaleString(locale)}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => eliminarUna(e, n.id)}
                    aria-label={t('notif.eliminar')}
                    className="flex-shrink-0 rounded p-1"
                    style={{ color: 'var(--yuda-text-secondary)' }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificacionesBell
