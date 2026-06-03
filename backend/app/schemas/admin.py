from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Roles válidos del sistema
ROLES_VALIDOS = {"admin", "vendedora", "contadora"}


class UsuarioCreate(BaseModel):
    """Datos para crear un usuario desde el panel de administración"""

    nombre: str
    email: str
    password: str
    rol: str

    @field_validator("password")
    @classmethod
    def validar_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")
        return v

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, v: str) -> str:
        if v not in ROLES_VALIDOS:
            raise ValueError("Rol inválido. Debe ser admin, vendedora o contadora")
        return v


class UsuarioUpdate(BaseModel):
    """Campos opcionales para actualizar un usuario"""

    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

    @field_validator("rol")
    @classmethod
    def validar_rol(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ROLES_VALIDOS:
            raise ValueError("Rol inválido. Debe ser admin, vendedora o contadora")
        return v


class UsuarioAdminResponse(BaseModel):
    """Datos de un usuario para el panel de administración"""

    id: str
    nombre: str
    email: str
    rol: str
    activo: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("rol", mode="before")
    @classmethod
    def rol_a_str(cls, v):
        # Convierte el enum RolUsuario a su valor string
        return v.value if hasattr(v, "value") else v


class ConfiguracionUpdate(BaseModel):
    """Actualización del tipo de cambio"""

    tipo_cambio_usd: float

    @field_validator("tipo_cambio_usd")
    @classmethod
    def validar_positivo(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("El tipo de cambio debe ser mayor que 0")
        return v


class ConfiguracionResponse(BaseModel):
    """Configuración actual del sistema"""

    tipo_cambio_usd: float
    updated_at: Optional[datetime]
