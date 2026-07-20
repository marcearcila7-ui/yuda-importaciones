from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClienteCreate(BaseModel):
    """Datos para crear un cliente del portal"""

    nombre: str
    email: str
    empresa: str | None = None
    nit: str | None = None
    telefono: str | None = None
    pais: str | None = None
    # Si no se envía contraseña, el backend genera una y la devuelve una sola vez
    password: str | None = None


class ClienteUpdate(BaseModel):
    """Campos editables de un cliente"""

    nombre: str | None = None
    empresa: str | None = None
    nit: str | None = None
    telefono: str | None = None
    pais: str | None = None
    activo: bool | None = None


class ClienteResponse(BaseModel):
    """Datos públicos de un cliente"""

    id: str
    nombre: str
    email: str
    empresa: str | None
    nit: str | None
    telefono: str | None
    pais: str | None
    vendedora_id: str
    activo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClienteCreado(ClienteResponse):
    """Respuesta al crear: incluye la contraseña inicial (se muestra una vez)"""

    password_inicial: str


class ResetPasswordRequest(BaseModel):
    nueva_password: str


class ClienteLogin(BaseModel):
    """Login del portal de clientes"""

    email: str
    password: str


class ClientePublic(BaseModel):
    """Datos del cliente que ve el propio cliente en el portal"""

    id: str
    nombre: str
    email: str
    empresa: str | None
    pais: str | None

    model_config = ConfigDict(from_attributes=True)


class ClienteTokenResponse(BaseModel):
    """Respuesta de un login exitoso en el portal"""

    access_token: str
    token_type: str = "bearer"
    cliente: ClientePublic
