from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MovimientoCreate(BaseModel):
    """Alta de un movimiento en la cuenta de un cliente.

    Si `comision_yuda` se omite, el backend la calcula como valor × 5%.
    `sesion_id` asocia el movimiento a un pedido (cotización) del cliente.
    """

    sesion_id: str | None = None
    contenedor_id: str | None = None
    envio: str | None = None
    fecha: date | None = None
    guia: str | None = None
    descripcion: str | None = None
    valor_mercancia: float = 0
    comision_yuda: float | None = None
    abono: float = 0
    nota: str | None = None


class MovimientoUpdate(BaseModel):
    """Edición parcial de un movimiento (los campos omitidos no cambian)."""

    sesion_id: str | None = None
    contenedor_id: str | None = None
    envio: str | None = None
    fecha: date | None = None
    guia: str | None = None
    descripcion: str | None = None
    valor_mercancia: float | None = None
    comision_yuda: float | None = None
    abono: float | None = None
    nota: str | None = None


class MovimientoResponse(BaseModel):
    """Un movimiento con su saldo acumulado (calculado, no almacenado)."""

    id: str
    cliente_id: str
    sesion_id: str | None
    contenedor_id: str | None
    envio: str | None
    fecha: date | None
    guia: str | None
    descripcion: str | None
    valor_mercancia: float
    comision_yuda: float
    abono: float
    saldo: float  # acumulado hasta este movimiento
    nota: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoCuenta(BaseModel):
    """Apartado de la cuenta correspondiente a UN pedido (cotización). Lleva su
    propio saldo, separado de los demás pedidos del cliente."""

    sesion_id: str | None  # None = movimientos "sin pedido"
    pedido_numero: str | None
    pedido_fecha: date | None
    es_pedido: bool  # True si la cotización ya entró al circuito de pedido
    compras_totales: float
    comision_total: float
    abonos_totales: float
    saldo_pendiente: float
    movimientos: list[MovimientoResponse]


class EstadoCuentaResponse(BaseModel):
    """Estado de cuenta del cliente: totales globales + apartados por pedido."""

    cliente_id: str
    nombre: str
    nit: str | None
    empresa: str | None
    # Totales del cliente = suma de todos sus pedidos
    compras_totales: float
    comision_total: float
    abonos_totales: float
    saldo_pendiente: float
    fecha_ultimo_abono: date | None
    pedidos: list[PedidoCuenta]
