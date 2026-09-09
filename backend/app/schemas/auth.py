from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Datos de entrada para iniciar sesión"""

    email: str
    password: str


class UsuarioResponse(BaseModel):
    """Datos públicos de un usuario"""

    id: str
    nombre: str
    email: str
    rol: str


class TokenResponse(BaseModel):
    """Respuesta de un login exitoso con el token y el usuario"""

    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse
