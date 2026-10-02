import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import { useAuthStore } from './store/authStore'
import { usePortalStore } from './store/portalStore'
import './index.css'
import './i18n'

// Monta el componente App en el nodo #root del index.html
// (deploy v3: CBM/MQT, foto final y confirmación previa a cotizar)
// La sesión guardada se restaura ANTES del primer render. Cuando esto vivía
// en un useEffect dentro de App, el primer render veía que no había sesión y
// la ruta protegida mandaba al login; la sesión se recuperaba un instante
// después, pero la URL ya se había perdido. En Yuda Logistic eso sacaba a la
// persona al recargar; en el cotizador no se notaba solo porque las pantallas
// se cargan de forma diferida y ese primer render alcanzaba a quedar en
// espera. Dependía de una carrera, así que ahora es explícito en los dos.
useAuthStore.getState().initFromStorage()
usePortalStore.getState().initFromStorage()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
