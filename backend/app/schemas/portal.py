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

    item_id: str
    foto_url: str | None = None
    # Referencia de catálogo de YUDA (la que pide el cliente)
    referencia: str | None = None
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
    # Cajas que el cliente pidió (null hasta que envíe su pedido).
    cantidad_solicitada: int | None = None


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
    # Pedido del cliente (cantidades + notas) enviado desde el portal.
    notas_cliente: str | None = None
    pedido_recibido: bool = False
    # Circuito de confirmación: recibido / por_confirmar / confirmado (null = sin pedido)
    pedido_estado: str | None = None
    pedido_confirmado: bool = False


class PortalPedidoLinea(BaseModel):
    """Una línea del pedido del cliente: cuántas cajas quiere de un producto"""

    item_id: str
    cantidad: int  # en cajas (CTNS)


class PortalPedidoInput(BaseModel):
    """Pedido que el cliente envía desde el portal"""

    items: list[PortalPedidoLinea]
    notas: str | None = None
