import portalClient from './portalClient'
import type { EstadoCuenta } from '../types/cuenta'
import type {
  CotizacionDetalle,
  CotizacionResumen,
  PortalPedidoInput,
  PortalTokenResponse,
} from '../types/portal'

export async function loginPortal(
  email: string,
  password: string,
): Promise<PortalTokenResponse> {
  const { data } = await portalClient.post<PortalTokenResponse>('/portal/login', {
    email,
    password,
  })
  return data
}

export async function getMisCotizaciones(): Promise<CotizacionResumen[]> {
  const { data } = await portalClient.get<CotizacionResumen[]>('/portal/cotizaciones')
  return data
}

export async function getCotizacionDetalle(sesion_id: string): Promise<CotizacionDetalle> {
  const { data } = await portalClient.get<CotizacionDetalle>(`/portal/cotizaciones/${sesion_id}`)
  return data
}

// El cliente envía las cajas que desea de cada producto + notas.
export async function enviarPedidoPortal(sesion_id: string, pedido: PortalPedidoInput): Promise<void> {
  await portalClient.put(`/portal/cotizaciones/${sesion_id}/pedido`, pedido)
}

// El cliente confirma las cantidades finales que le envió la vendedora.
export async function confirmarPedidoPortal(sesion_id: string): Promise<void> {
  await portalClient.post(`/portal/cotizaciones/${sesion_id}/confirmar`)
}

export async function descargarCotizacion(
  sesion_id: string,
  idioma: string,
  tipo: 'excel' | 'pdf',
): Promise<Blob> {
  const { data } = await portalClient.post<Blob>(
    `/portal/cotizaciones/${sesion_id}/cotizacion-${tipo}`,
    { idioma },
    { responseType: 'blob' },
  )
  return data
}

// Estado de cuenta del propio cliente (solo lectura).
export async function getMiCuenta(): Promise<EstadoCuenta> {
  const { data } = await portalClient.get<EstadoCuenta>('/portal/cuenta')
  return data
}
