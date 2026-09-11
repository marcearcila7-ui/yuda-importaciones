from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator

IDIOMAS_VALIDOS = {"es", "en", "zh"}


class CotizacionRequest(BaseModel):
    """Solicitud de exportación de cotización"""

    idioma: str
    # Claves de CLAVES_COLUMNAS (cotizacion_service.py) a mostrar en el
    # documento; None (o ausente) muestra todas, como siempre. Foto y
    # Referencia salen sí o sí aunque no vengan en la lista.
    columnas: Optional[list[str]] = None

    @field_validator("idioma")
    @classmethod
    def validar_idioma(cls, v: str) -> str:
        if v not in IDIOMAS_VALIDOS:
            raise ValueError("Idioma inválido. Debe ser es, en o zh")
        return v


class CotizacionInfo(BaseModel):
    """Información de una cotización generada"""

    numero: str
    sesion_id: str
    nombre_cliente: str
    idioma: str
    fecha: date
