from datetime import date, datetime

from pydantic import BaseModel


class EmpleadaResumen(BaseModel):
    """Empleada disponible para asociar a un pedido / ranking."""

    id: str
    nombre: str


class PedidoTiendaCreate(BaseModel):
    """Alta de un pedido a tienda."""

    nombre_tienda: str
    fecha_pedido: date | None = None
    monto_total: float = 0
    fecha_pago_30: date | None = None
    fecha_estimada_entrega: date | None = None
    fecha_real_entrega: date | None = None
    fecha_estimada_pago_70: date | None = None
    fecha_pago_70: date | None = None
    pct_comision_tienda: float = 0
    fecha_comision: date | None = None
    empleada_id: str | None = None
    notas: str | None = None


class PedidoTiendaUpdate(BaseModel):
    """Edición parcial de un pedido a tienda (campos omitidos no cambian)."""

    nombre_tienda: str | None = None
    fecha_pedido: date | None = None
    monto_total: float | None = None
    fecha_pago_30: date | None = None
    fecha_estimada_entrega: date | None = None
    fecha_real_entrega: date | None = None
    fecha_estimada_pago_70: date | None = None
    fecha_pago_70: date | None = None
    pct_comision_tienda: float | None = None
    fecha_comision: date | None = None
    empleada_id: str | None = None
    notas: str | None = None


class PedidoTiendaResponse(BaseModel):
    """Pedido a tienda con los montos y el estado calculados."""

    id: str
    nombre_tienda: str
    fecha_pedido: date | None
    monto_total: float
    # 30/70/comisión calculados del total (CNY)
    monto_30: float
    monto_70: float
    monto_comision: float
    fecha_pago_30: date | None
    fecha_estimada_entrega: date | None
    fecha_real_entrega: date | None
    fecha_estimada_pago_70: date | None
    fecha_pago_70: date | None
    pct_comision_tienda: float
    fecha_comision: date | None
    empleada_id: str | None
    empleada_nombre: str | None
    notas: str | None
    estado: str  # pendiente / parcial / pagado
    dias_para_pago_70: int | None
    alerta_pago_70: bool
    created_at: datetime


class ComisionItem(BaseModel):
    """Una comisión recibida (derivada de un pedido a tienda)."""

    pedido_id: str
    nombre_tienda: str
    pct_comision_tienda: float
    monto_comision: float
    fecha_comision: date | None
    fecha_pedido: date | None
    empleada_nombre: str | None


class ComisionesReporte(BaseModel):
    """Comisiones recibidas en un período con su total."""

    items: list[ComisionItem]
    total_comision: float
    desde: date | None
    hasta: date | None
