import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import es from './es.json'
import en from './en.json'
import zh from './zh.json'

// Idioma guardado en localStorage; por defecto español
const idiomaGuardado = localStorage.getItem('yuda_idioma') || 'es'

i18n.use(initReactI18next).init({
  resources: {
    es: { translation: es },
    en: { translation: en },
    zh: { translation: zh },
  },
  lng: idiomaGuardado,
  fallbackLng: 'es',
  interpolation: { escapeValue: false },
})

export default i18n
