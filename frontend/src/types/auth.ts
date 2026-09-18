export interface Usuario {
  id: string
  nombre: string
  email: string
  rol: 'admin' | 'vendedora' | 'contadora' | 'bodega'
}

export interface TokenResponse {
  access_token: string
  token_type: string
  usuario: Usuario
}
