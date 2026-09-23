from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


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
    whatsapp: str | None = None
    # Correo real para avisos (Brevo); None si nunca se guardó uno distinto
    # del `email` de login del portal (ver modelo).
    email_contacto: str | None = None
    pais: str | None
    vendedora_id: str
    sigla: str | None = None
    activo: bool
    origen: str = "manual"
    # True si vino de una importación de Yuda Contable y todavía nadie lo
    # asignó a una vendedora de verdad (sigue a nombre del admin que
    # importó). El frontend lo usa para separarlo de los clientes reales en
    # vez de mezclarlos en la misma lista.
    pendiente_asignacion: bool = False
    # True si todavía tiene la clave de plantilla de la importación masiva de
    # Yuda Contable sin cambiar (el portal se lo exige en su próximo ingreso).
    debe_cambiar_password: bool = False
    estado_cuenta_oficial_url: str | None = None
    estado_cuenta_oficial_actualizado_en: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    # True con la clave de plantilla de la importación masiva: el portal
    # bloquea todo lo demás hasta que la cambie por una propia.
    debe_cambiar_password: bool = False

    model_config = ConfigDict(from_attributes=True)


class CambiarPasswordInput(BaseModel):
    password_actual: str
    password_nueva: str

    @field_validator("password_nueva")
    @classmethod
    def _validar_nueva(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La nueva contraseña debe tener al menos 6 caracteres")
        return v


class CambiarPasswordResponse(BaseModel):
    """Nueva contraseña puesta: se manda un token nuevo porque cambiar la
    clave invalida el token viejo (mismo mecanismo que un reset)."""

    access_token: str
    token_type: str = "bearer"


class ClienteTokenResponse(BaseModel):
    """Respuesta de un login exitoso en el portal"""

    access_token: str
    token_type: str = "bearer"
    cliente: ClientePublic


class MagicLoginInput(BaseModel):
    """Enlace de un aviso automático (ej. "tu pedido está listo para
    aprobar"): entra directo sin pedir contraseña."""

    token: str


class MagicLoginResponse(ClienteTokenResponse):
    """Igual que un login normal, más a qué cotización llevar al cliente."""

    sesion_id: str


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


class ContableClientePreview(BaseModel):
    """Un cliente de Yuda Contable comparado contra lo que ya hay acá."""

    sigla: str
    nombre: str | None
    pais: str | None
    telefono: str | None
    ya_existe: bool
    cliente_id_existente: str | None = None


class ImportarContableInput(BaseModel):
    siglas: list[str]


class ImportarContableUnoInput(BaseModel):
    """Importa un solo cliente encontrado por búsqueda en vivo (a diferencia
    de ImportarContableInput, que trae varios de la lista fija de una vez)."""

    sigla: str


class SincronizarClienteContableInput(BaseModel):
    """Lo que manda Yuda Contable (app aparte) cuando Marcela crea un cliente
    ahí y elige sincronizarlo de una vez -en vez de esperar a que alguien lo
    busque e importe manualmente después."""

    sigla: str
    nombre: str | None = None
    telefono: str | None = None
    whatsapp: str | None = None
    email: str | None = None
    pais: str | None = None


class AccionClienteContableInput(BaseModel):
    """Yuda Contable manda esto al eliminar o desactivar un cliente allá,
    para que el cotizador haga lo mismo del lado suyo."""

    sigla: str


class ImportarContableResultado(BaseModel):
    creados: int
    omitidos: int


class ClienteColaboracionResponse(BaseModel):
    """Vista consolidada de un cliente: quién lo gestiona, todas sus
    cotizaciones (de cualquier vendedora) y la bitácora de actividad. La usa
    Marcela para armar la factura final y las vendedoras que comparten un
    cliente para ver el trabajo de las demás."""

    duena: VendedoraBasica
    asignadas: list[VendedoraAsignadaResponse]
    cotizaciones: list[CotizacionResumenCliente]
    actividad: list[ActividadResponse]
