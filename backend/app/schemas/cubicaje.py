from datetime import datetime

from pydantic import BaseModel


class CubicajeResumen(BaseModel):
    """Estado actual del cubicaje calculado en vivo (con las correcciones de
    bodega si las hay), para mostrarlo mientras se llena el reporte."""

    cbm_calculado: float
    limite_min: float
    limite_max: float
    resultado: str  # "sobra" | "falta" | "ajustado"
    referencias: list[str]  # referencias reales del pedido, para el selector


class CubicajeMensajeResponse(BaseModel):
    id: str
    tipo: str
    autor_id: str
    autor_nombre: str | None = None
    mensaje: str | None = None
    cbm_calculado: float | None = None
    resultado: str | None = None
    referencia: str | None = None
    cajas_afectadas: int | None = None
    espacio_restante_cbm: float | None = None
    created_at: datetime


class CubicajeDetalle(BaseModel):
    """Lo que consumen ambas apps (bodega y cotizador): el cálculo en vivo más
    todo el hilo, en una sola llamada -así el polling rápido no necesita dos
    pedidos separados."""

    resumen: CubicajeResumen
    mensajes: list[CubicajeMensajeResponse]


class CubicajeReporteInput(BaseModel):
    """Bodega manda un reporte: elige si sobró (con referencia+cajas) o si
    falta cubicaje (el sistema calcula el espacio restante solo). El
    cbm_calculado y el resultado real los decide siempre el servidor -esto
    solo dice qué datos adicionales completar."""

    resultado: str  # "sobra" | "falta" | "ajustado"
    referencia: str | None = None
    cajas_afectadas: int | None = None
    nota: str | None = None


class CubicajeNotaInput(BaseModel):
    mensaje: str


class CubicajeRespuestaInput(BaseModel):
    mensaje: str
