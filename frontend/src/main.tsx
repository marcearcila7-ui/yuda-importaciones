import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './i18n'

// Monta el componente App en el nodo #root del index.html
// (deploy v2: CBM/MQT, foto final y confirmación previa a cotizar)
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
