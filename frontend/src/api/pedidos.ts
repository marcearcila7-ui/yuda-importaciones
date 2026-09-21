import apiClient from './client'
import type { GenerarPedidosResponse, PedidoBodegaSeguimiento, PedidoGenerado } from '../types/pedidos'

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

// Fecha aproximada que dio ESTE proveedor (no toda la cotización). Si cambió
// de verdad, el backend le avisa al cliente por correo y WhatsApp.
export async function actualizarFechaTentativa(
  pedidoGeneradoId: string,
  fecha: string,
): Promise<PedidoGenerado> {
  const { data } = await apiClient.patch<PedidoGenerado>(
    `/pedidos/${pedidoGeneradoId}/fecha-tentativa`,
    { fecha },
  )
  return data
}

export async function descargarZip(sesion_id: string): Promise<Blob> {
  const { data } = await apiClient.get(`/pedidos/${sesion_id}/descargar-zip`, {
    responseType: 'blob',
  })
  return data as Blob
}

// Reemplaza el Excel/PDF/CSV generado de una orden a proveedor por una
// versión corregida a mano, por si la vendedora necesita ajustar algo antes
// de que bodega lo vea.
export async function reemplazarArchivoPedidoGenerado(
  pedidoGeneradoId: string,
  archivo: File,
): Promise<PedidoGenerado> {
  const formData = new FormData()
  formData.append('archivo', archivo)
  const { data } = await apiClient.post<PedidoGenerado>(
    `/pedidos/generados/${pedidoGeneradoId}/reemplazar-archivo`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } },
  )
  return data
}

export interface UsuarioBodega {
  id: string
  nombre: string
}

// Admin + bodega activos, para elegir a quién asignar al enviar el pedido.
export async function listarUsuariosBodega(): Promise<UsuarioBodega[]> {
  const { data } = await apiClient.get<UsuarioBodega[]>('/bodega/usuarios')
  return data
}

// Botón guiado: envía el pedido a bodega y, si se eligió, lo asigna directo a
// alguien de bodega en el mismo paso.
export async function enviarABodegaGuiado(
  sesion_id: string,
  asignadoAId: string | null,
): Promise<{ estado: string; bodega_asignado_a_id: string | null }> {
  const { data } = await apiClient.post(`/pedidos/${sesion_id}/enviar-a-bodega`, {
    asignado_a_id: asignadoAId,
  })
  return data
}

// Panel de control: todo lo que se ha enviado a bodega, sin importar el
// cliente. Admin ve todas; la vendedora solo las suyas.
export async function getBodegaResumen(): Promise<PedidoBodegaSeguimiento[]> {
  const { data } = await apiClient.get<PedidoBodegaSeguimiento[]>('/pedidos/bodega-resumen')
  return data
}

// Reasignar un pedido directo desde el panel de la vendedora (mismo endpoint
// que usa Yuda Logistic; el backend limita a sus propios pedidos).
export async function asignarPedidoBodega(
  sesionId: string,
  asignadoAId: string | null,
): Promise<{ bodega_asignado_a_id: string | null; bodega_asignado_a_nombre: string | null }> {
  const { data } = await apiClient.patch(`/bodega/pedidos/${sesionId}/asignar`, {
    asignado_a_id: asignadoAId,
  })
  return data
}
