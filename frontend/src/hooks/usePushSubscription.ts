import { useEffect } from 'react'
import { desuscribirPush, getVapidPublicKey, suscribirPush } from '../api/push'

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const rawData = window.atob(base64)
  const outputArray = new Uint8Array(rawData.length)
  for (let i = 0; i < rawData.length; i++) {
    outputArray[i] = rawData.charCodeAt(i)
  }
  return outputArray
}

/**
 * Activa las notificaciones push reales (con el navegador cerrado o el
 * celular en reposo) para el usuario que inició sesión. Todo esto es "mejor
 * esfuerzo": si el navegador no soporta push, o el usuario nunca da permiso,
 * la campanita in-app sigue funcionando igual -esto es un plus, no un
 * reemplazo.
 */
export function usePushSubscription(activo: boolean): void {
  useEffect(() => {
    if (!activo) return
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return

    let cancelado = false

    const registrar = async () => {
      try {
        const registro = await navigator.serviceWorker.register('/sw.js')

        if (Notification.permission === 'denied') return
        if (Notification.permission === 'default') {
          const permiso = await Notification.requestPermission()
          if (permiso !== 'granted') return
        }
        if (cancelado) return

        let suscripcion = await registro.pushManager.getSubscription()
        if (!suscripcion) {
          const claveVapid = await getVapidPublicKey()
          if (!claveVapid || cancelado) return
          suscripcion = await registro.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(claveVapid) as BufferSource,
          })
        }

        const json = suscripcion.toJSON()
        if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) return
        await suscribirPush({
          endpoint: json.endpoint,
          p256dh: json.keys.p256dh,
          auth: json.keys.auth,
        })
      } catch {
        // Mejor esfuerzo: si algo falla acá, la app sigue funcionando con
        // la campanita in-app nada más.
      }
    }

    registrar()
    return () => {
      cancelado = true
    }
  }, [activo])
}

/** Al cerrar sesión, se le avisa al backend que este navegador ya no debe
 * recibir push a nombre de nadie (la próxima persona que inicie sesión en
 * este mismo navegador vuelve a suscribirse a su propio nombre). */
export async function desuscribirPushDelNavegador(): Promise<void> {
  try {
    if (!('serviceWorker' in navigator)) return
    const registro = await navigator.serviceWorker.getRegistration('/sw.js')
    if (!registro) return
    const suscripcion = await registro.pushManager.getSubscription()
    if (!suscripcion) return
    await desuscribirPush(suscripcion.endpoint)
  } catch {
    // Mejor esfuerzo: si falla, la suscripción vieja simplemente se
    // sobrescribe la próxima vez que alguien inicie sesión acá.
  }
}
