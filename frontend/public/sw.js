// Service worker: solo se encarga de mostrar notificaciones push y de llevar
// al usuario a la cotización correspondiente al tocarlas, incluso con la app
// cerrada o el celular en reposo. No cachea nada (no es para trabajar offline).

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  let datos = {}
  try {
    datos = event.data ? event.data.json() : {}
  } catch {
    datos = {}
  }
  const titulo = datos.titulo || 'YUDA Importaciones'
  const opciones = {
    body: datos.mensaje || '',
    icon: '/icon-192.png',
    badge: '/favicon-32.png',
    data: { sesion_id: datos.sesion_id || null },
  }
  event.waitUntil(self.registration.showNotification(titulo, opciones))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const sesionId = event.notification.data && event.notification.data.sesion_id
  const url = sesionId ? `/cotizacion/${sesionId}` : '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((lista) => {
      for (const c of lista) {
        if ('focus' in c) {
          c.navigate(url)
          return c.focus()
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url)
    }),
  )
})
