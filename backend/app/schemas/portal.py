from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.seguimiento import SeguimientoResponse


class PortalCotizacionResumen(BaseModel):
    """Fila del listado de cotizaciones del cliente"""

    sesion_id: str
    numero: str
    nombre_cliente: str
    fecha: date
    total_items: int
    total_usd: float
    estado: str
    actualizado: datetime | None = None


class PortalItem(BaseModel):
    """Producto tal como lo ve el cliente (sin datos del proveedor)"""

    foto_url: str | None = None
    descripcion_es: str | None = None
    descripcion_en: str | None = None
    descripcion_zh: str | None = None
    ctns: int
    qty_por_ctn: int
    t_qty: int
    price_usd: float
    total_usd: float
    cbm: float
    t_cbm: float


class PortalCotizacionDetalle(BaseModel):
    """Detalle de una cotización para el cliente"""

    sesion_id: str
    numero: str
    nombre_cliente: str
    fecha: date
    items: list[PortalItem]
    total_usd: float
    total_cbm: float
    seguimiento: SeguimientoResponse
