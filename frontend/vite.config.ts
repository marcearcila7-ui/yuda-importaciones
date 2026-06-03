import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from 'tailwindcss'
import autoprefixer from 'autoprefixer'

// En Docker el backend es accesible por el nombre del servicio "backend";
// en local se usa localhost. Se controla con la variable VITE_API_TARGET.
const apiTarget = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  // PostCSS se configura aquí para no necesitar un archivo postcss.config aparte
  css: {
    postcss: {
      plugins: [tailwindcss, autoprefixer],
    },
  },
  server: {
    host: true,
    port: 3000,
    // Redirige /api y /uploads hacia el backend (docker o local)
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/uploads': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
