export interface Notificacion {
  id: string
  sesion_id: string | null
  tipo: string
  titulo: string
  mensaje: string | null
  leida: boolean
  created_at: string
}
