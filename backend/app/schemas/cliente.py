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
    # Reasignar la vendedora dueña: exclusivo de admin (se valida en la ruta).
    vendedora_id: str | None = None
    # Código de Yuda Contable: exclusivo de admin (se valida en la ruta).
    sigla: str | None = None


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
    sigla: str | None = None
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


# ──────────────── Colaboración: clientes compartidos entre vendedoras ────────────────


class VendedoraBasica(BaseModel):
    id: str
    nombre: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class VendedoraAsignadaResponse(BaseModel):
    """Una vendedora adicional (no la dueña) con acceso al cliente."""

    vendedora: VendedoraBasica
    asignado_por: str | None = None
    created_at: datetime


class AsignarVendedorasInput(BaseModel):
    vendedora_ids: list[str]


class ActividadInput(BaseModel):
    nota: str


class ActividadResponse(BaseModel):
    id: str
    usuario_id: str
    usuario_nombre: str
    nota: str
    created_at: datetime


class CotizacionResumenCliente(BaseModel):
    """Una cotización del cliente, con quién la hizo, para la vista de Marcela."""

    sesion_id: str
    numero: str
    fecha: datetime
    vendedora_nombre: str
    pedido_estado: str | None = None
    estado_envio: str | None = None


class ClienteColaboracionResponse(BaseModel):
    """Vista consolidada de un cliente: quién lo gestiona, todas sus
    cotizaciones (de cualquier vendedora) y la bitácora de actividad. La usa
    Marcela para armar la factura final y las vendedoras que comparten un
    cliente para ver el trabajo de las demás."""

    duena: VendedoraBasica
    asignadas: list[VendedoraAsignadaResponse]
    cotizaciones: list[CotizacionResumenCliente]
    actividad: list[ActividadResponse]
