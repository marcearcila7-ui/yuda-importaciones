import axios from 'axios'
import apiClient from './client'
import { TIMEOUT_SUBIDA } from '../lib/imagenes'
import type { OCRResponse } from '../types/ocr'

// Sube una foto al endpoint de OCR y devuelve los datos extraídos
export async function subirFotoOCR(archivo: File): Promise<OCRResponse> {
  const formData = new FormData()
  formData.append('foto', archivo)

  const token = localStorage.getItem('yuda_token')

  try {
    const { data } = await apiClient.post<OCRResponse>('/ocr/extraer', formData, {
      headers: { Authorization: `Bearer ${token}` },
      // Sin timeout, una subida estancada se quedaba girando para siempre.
      timeout: TIMEOUT_SUBIDA,
    })
    return data
  } catch (err) {
    // Conserva el mensaje del backend si viene; si no, uno genérico
    let detalle = 'No se pudo procesar la imagen'
    if (axios.isAxiosError(err)) {
      if (err.response?.data?.detail) {
        detalle = err.response.data.detail
      } else if (err.code === 'ECONNABORTED' || err.code === 'ERR_NETWORK') {
        detalle = 'Se cortó la conexión al subir la foto. Revisa la señal y reintenta.'
      }
    }
    throw new Error(detalle)
  }
}
