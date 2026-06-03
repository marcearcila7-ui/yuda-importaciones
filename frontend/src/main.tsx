import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

// Monta el componente App en el nodo #root del index.html
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
