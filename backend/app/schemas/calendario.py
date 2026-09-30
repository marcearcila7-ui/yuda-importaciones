from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TareaInput(BaseModel):
    fecha: date
    tipo: str  # "recibe" | "carga"
    marca_cliente: str
    descripcion: str | None = None


class TareaResponse(BaseModel):
    id: str
    fecha: date
    tipo: str
    marca_cliente: str
    descripcion: str | None = None
    creado_por_id: str
    creado_por_nombre: str
    creado_en: datetime
    actualizado_por_id: str | None = None
    actualizado_por_nombre: str | None = None
    actualizado_en: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class FeriadoResponse(BaseModel):
    fecha: date
    nombre_es: str
    nombre_en: str


class CalendarioNotificacionResponse(BaseModel):
    id: str
    tarea_id: str
    tipo: str
    titulo: str
    mensaje: str | None = None
    leida: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
