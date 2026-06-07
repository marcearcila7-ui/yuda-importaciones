import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Bell, Check } from 'lucide-react'
import { getNotificaciones, marcarLeida, marcarTodasLeidas } from '../api/notificaciones'
import type { Notificacion } from '../types/notificacion'

const LOCALES: Record<string, string> = { es: 'es-ES', en: 'en-US', zh: 'zh-CN' }

// Campana de avisos para Marcela: muestra las cotizaciones listas para cargar BL.
// Refresca cada 60s para no requerir recargar la página.
function NotificacionesBell() {
  const { t, i18n } = useTranslation()
  const [items, setItems] = useState<Notificacion[]>([])
  const [abierto, setAbierto] = useState(false)
  const cajaRef = useRef<HTMLDivElement>(null)

  const cargar = () => {
    getNotificaciones().then(setItems).catch(() => {})
  }

  useEffect(() => {
    cargar()
    const id = setInterval(cargar, 60000)
    return () => clearInterval(id)
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

  const leerUna = async (n: Notificacion) => {
    if (n.leida) return
    setItems((xs) => xs.map((x) => (x.id === n.id ? { ...x, leida: true } : x)))
    try {
      await marcarLeida(n.id)
    } catch {
      cargar()
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

  return (
    <div className="relative" ref={cajaRef}>
      <button
        type="button"
        onClick={() => setAbierto((v) => !v)}
        className="relative flex h-9 w-9 items-center justify-center rounded-full"
        style={{ backgroundColor: '#1F1F1F', color: '#FFFFFF' }}
        aria-label={t('notif.titulo')}
      >
        <Bell size={18} />
        {noLeidas > 0 && (
          <span
            className="absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full px-1 text-xs font-bold text-white"
            style={{ backgroundColor: '#EF4444' }}
          >
            {noLeidas > 9 ? '9+' : noLeidas}
          </span>
        )}
      </button>

      {abierto && (
        <div
          className="absolute bottom-12 left-0 z-50 w-80 overflow-hidden rounded-xl bg-white"
          style={{ boxShadow: '0 10px 30px rgba(0,0,0,0.25)' }}
        >
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <p className="text-sm font-bold" style={{ color: '#0D0D0D' }}>
              {t('notif.titulo')}
            </p>
            {noLeidas > 0 && (
              <button
                type="button"
                onClick={leerTodas}
                className="flex items-center gap-1 text-xs font-medium"
                style={{ color: '#4B52E8' }}
              >
                <Check size={14} /> {t('notif.marcarTodas')}
              </button>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            {items.length === 0 ? (
              <p className="px-4 py-6 text-center text-sm" style={{ color: '#9CA3AF' }}>
                {t('notif.sinAvisos')}
              </p>
            ) : (
              items.map((n) => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => leerUna(n)}
                  className="flex w-full flex-col gap-1 border-b border-gray-50 px-4 py-3 text-left"
                  style={{ backgroundColor: n.leida ? '#FFFFFF' : '#EEF0FD' }}
                >
                  <div className="flex items-center gap-2">
                    {!n.leida && (
                      <span className="h-2 w-2 flex-shrink-0 rounded-full" style={{ backgroundColor: '#4B52E8' }} />
                    )}
                    <span className="text-sm font-semibold" style={{ color: '#0D0D0D' }}>
                      {n.titulo}
                    </span>
                  </div>
                  {n.mensaje && (
                    <span className="text-xs" style={{ color: '#6B7280' }}>
                      {n.mensaje}
                    </span>
                  )}
                  <span className="text-xs" style={{ color: '#9CA3AF' }}>
                    {new Date(n.created_at).toLocaleString(locale)}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificacionesBell
