from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.contenedor import ESTADOS_CONTENEDOR


class ContenedorCreate(BaseModel):
    """Datos para crear un contenedor/embarque"""

    codigo: str
    trm_usd: float
    fecha: date | None = None
    estado: str = "abierto"
    notas: str | None = None

    @field_validator("trm_usd")
    @classmethod
    def trm_positiva(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("La TRM debe ser mayor a 0")
        return v

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v: str) -> str:
        if v not in ESTADOS_CONTENEDOR:
            raise ValueError(f"Estado inválido. Use uno de: {', '.join(ESTADOS_CONTENEDOR)}")
        return v


class ContenedorUpdate(BaseModel):
    """Campos editables de un contenedor (todos opcionales)"""

    codigo: str | None = None
    trm_usd: float | None = None
    fecha: date | None = None
    estado: str | None = None
    notas: str | None = None

    @field_validator("trm_usd")
    @classmethod
    def trm_positiva(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("La TRM debe ser mayor a 0")
        return v

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v: str | None) -> str | None:
        if v is not None and v not in ESTADOS_CONTENEDOR:
            raise ValueError(f"Estado inválido. Use uno de: {', '.join(ESTADOS_CONTENEDOR)}")
        return v


class ContenedorResponse(BaseModel):
    """Datos públicos de un contenedor"""

    id: str
    codigo: str
    trm_usd: float
    fecha: date | None
    estado: str
    notas: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
