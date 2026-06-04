from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.seguimiento import ESTADOS_ENVIO


class HitoInput(BaseModel):
    """Fecha y nota opcionales de un hito"""

    fecha: str | None = None
    nota: str | None = None


class SeguimientoUpdate(BaseModel):
    """Actualización del seguimiento (vendedora / admin)"""

    estado: str
    novedades: str | None = None
    numero_tracking: str | None = None
    naviera: str | None = None
    url_tracking: str | None = None
    fecha_eta: date | None = None
    hitos: dict[str, HitoInput] | None = None

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, v: str) -> str:
        if v not in ESTADOS_ENVIO:
            raise ValueError(f"Estado inválido. Debe ser uno de: {', '.join(ESTADOS_ENVIO)}")
        return v

    @field_validator("hitos")
    @classmethod
    def validar_hitos(cls, v: dict | None) -> dict | None:
        if v is None:
            return v
        for clave in v:
            if clave not in ESTADOS_ENVIO:
                raise ValueError(f"Hito inválido: {clave}")
        return v


class SeguimientoResponse(BaseModel):
    """Estado del seguimiento"""

    estado: str
    novedades: str | None = None
    numero_tracking: str | None = None
    naviera: str | None = None
    url_tracking: str | None = None
    fecha_eta: date | None = None
    hitos: dict | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
