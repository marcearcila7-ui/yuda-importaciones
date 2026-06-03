import axios from 'axios'
import apiClient from './client'
import type { OCRResponse } from '../types/ocr'

// Sube una foto al endpoint de OCR y devuelve los datos extraídos
export async function subirFotoOCR(archivo: File): Promise<OCRResponse> {
  const formData = new FormData()
  formData.append('foto', archivo)

  const token = localStorage.getItem('yuda_token')

  try {
    const { data } = await apiClient.post<OCRResponse>('/ocr/extraer', formData, {
      headers: { Authorization: `Bearer ${token}` },
    })
    return data
  } catch (err) {
    // Conserva el mensaje del backend si viene; si no, uno genérico
    let detalle = 'No se pudo procesar la imagen'
    if (axios.isAxiosError(err) && err.response?.data?.detail) {
      detalle = err.response.data.detail
    }
    throw new Error(detalle)
  }
}
