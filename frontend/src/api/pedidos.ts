import apiClient from './client'
import type { GenerarPedidosResponse, PedidoGenerado } from '../types/pedidos'

// Adjunta el token de localStorage en cada request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('yuda_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// usarCantidadesCliente: usa las cajas que pidió el cliente en su portal (Fase 3).
export async function generarPedidos(
  sesion_id: string,
  usarCantidadesCliente = false,
): Promise<GenerarPedidosResponse> {
  const { data } = await apiClient.post<GenerarPedidosResponse>(
    `/pedidos/${sesion_id}/generar`,
    null,
    {
      params: { usar_cantidades_cliente: usarCantidadesCliente },
      // Genera Excel+PDF con fotos por proveedor: puede tardar. Timeout amplio para
      // no quedar colgado indefinidamente y dar un error claro si algo falla.
      timeout: 180000,
    },
  )
  return data
}

export async function getPedidos(sesion_id: string): Promise<PedidoGenerado[]> {
  const { data } = await apiClient.get<PedidoGenerado[]>(`/pedidos/${sesion_id}`)
  return data
}

export async function descargarZip(sesion_id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/pedidos/${sesion_id}/descargar-zip`, {
    responseType: 'blob',
  })
  return data as Blob
}
