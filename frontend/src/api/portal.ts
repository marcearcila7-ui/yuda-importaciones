import portalClient from './portalClient'
import type {
  CotizacionDetalle,
  CotizacionResumen,
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
