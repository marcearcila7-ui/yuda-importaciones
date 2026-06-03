from datetime import date

from pydantic import BaseModel, field_validator

IDIOMAS_VALIDOS = {"es", "en", "zh"}


class CotizacionRequest(BaseModel):
    """Solicitud de exportación de cotización"""

    idioma: str

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
