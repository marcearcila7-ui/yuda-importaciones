from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PagoInput(BaseModel):
    fecha: date
    tienda: str
    cliente_id: str
    monto: Decimal
    estatus: str  # "pagado" | "no_pagado" | "aplazado"


class PagoResponse(BaseModel):
    id: str
    fecha: date
    tienda: str
    cliente_id: str
    cliente_sigla: str
    monto: Decimal
    estatus: str
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
