from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.cuenta import MONEDAS


def _validar_moneda(v: str | None) -> str | None:
    if v is not None and v not in MONEDAS:
        raise ValueError(f"Moneda inválida. Use una de: {', '.join(MONEDAS)}")
    return v


class MovimientoCreate(BaseModel):
    """Alta de un movimiento en la cuenta de un cliente.

    Si `comision_yuda` se omite, el backend la calcula como valor × 5%.
    `sesion_id` asocia el movimiento a un pedido (cotización) del cliente.
    `moneda` es la moneda de cobro del pedido (USD/COP/RMB/EUR).
    """

    sesion_id: str | None = None
    contenedor_id: str | None = None
    moneda: str = "USD"
    envio: str | None = None
    fecha: date | None = None
    guia: str | None = None
    descripcion: str | None = None
    valor_mercancia: float = 0
    comision_yuda: float | None = None
    abono: float = 0
    # De donde salio el abono: monto como entro, su moneda y la tasa del dia.
    # Con los tres, el backend calcula el abono y no hace falta mandarlo.
    monto_origen: float | None = None
    moneda_origen: str | None = None
    tasa_cambio: float | None = None
    nota: str | None = None

    @field_validator("moneda")
    @classmethod
    def _moneda_ok(cls, v: str) -> str:
        return _validar_moneda(v)


class MovimientoUpdate(BaseModel):
    """Edición parcial de un movimiento (los campos omitidos no cambian)."""

    sesion_id: str | None = None
    contenedor_id: str | None = None
    moneda: str | None = None
    envio: str | None = None
    fecha: date | None = None
    guia: str | None = None
    descripcion: str | None = None
    valor_mercancia: float | None = None
    comision_yuda: float | None = None
    abono: float | None = None
    monto_origen: float | None = None
    moneda_origen: str | None = None
    tasa_cambio: float | None = None
    nota: str | None = None

    @field_validator("moneda")
    @classmethod
    def _moneda_ok(cls, v: str | None) -> str | None:
        return _validar_moneda(v)


class MovimientoResponse(BaseModel):
    """Un movimiento con su saldo acumulado (calculado, no almacenado)."""

    id: str
    cliente_id: str
    sesion_id: str | None
    contenedor_id: str | None
    moneda: str
    envio: str | None
    fecha: date | None
    guia: str | None
    descripcion: str | None
    valor_mercancia: float
    comision_yuda: float
    abono: float
    # Como entro el abono, cuando se pago en otra moneda
    monto_origen: float | None = None
    moneda_origen: str | None = None
    tasa_cambio: float | None = None
    saldo: float  # acumulado hasta este movimiento
    nota: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PedidoCuenta(BaseModel):
    """Apartado de la cuenta correspondiente a UN pedido (cotización). Lleva su
    propio saldo y su moneda, separado de los demás pedidos del cliente."""

    sesion_id: str | None  # None = movimientos "sin pedido"
    pedido_numero: str | None
    pedido_fecha: date | None
    es_pedido: bool  # True si la cotización ya entró al circuito de pedido
    moneda: str
    compras_totales: float
    comision_total: float
    abonos_totales: float
    saldo_pendiente: float
    movimientos: list[MovimientoResponse]


class PedidoContable(BaseModel):
    """Un pedido de Yuda Contable, ya calculado allá (FIFO, con intereses)."""

    numero_pedido: str
    fecha_pedido: str | None
    total: float
    pendiente: float
    estado: str
    dias: int


class AbonoContable(BaseModel):
    fecha_abono: str | None
    monto: float
    numero_pedido: str | None
    estado: str
    es_saldo_a_favor: bool


class EstadoCuentaContableResponse(BaseModel):
    """Estado de cuenta REAL de Yuda Contable (app aparte), traído en vivo
    por su API interna -no tiene relación con la cuenta interna de arriba
    (MovimientoCuenta). None en el campo del cliente si no se pudo traer."""

    sigla: str
    moneda: str
    saldo_pendiente: float
    es_a_favor: bool
    otros_conceptos_pendientes: float
    saldo_a_favor: float
    dias_vencido: int | None
    estado_atraso: str | None
    pedidos: list[PedidoContable]
    abonos_recientes: list[AbonoContable]


class TotalMoneda(BaseModel):
    """Totales del cliente en UNA moneda (no se suman monedas distintas)."""

    moneda: str
    compras_totales: float
    comision_total: float
    abonos_totales: float
    saldo_pendiente: float


class EstadoCuentaResponse(BaseModel):
    """Estado de cuenta del cliente: totales por moneda + apartados por pedido."""

    cliente_id: str
    nombre: str
    nit: str | None
    empresa: str | None
    # Como cada pedido puede tener otra moneda, los totales van agrupados por moneda.
    totales_por_moneda: list[TotalMoneda]
    fecha_ultimo_abono: date | None
    pedidos: list[PedidoCuenta]
    # Documento real de Yuda Contable (PDF/imagen) que Marcela subió a mano;
    # no tiene relación con los totales de arriba (esos son de la cuenta
    # interna del cotizador). None si nunca se subió ninguno. Se usa solo
    # como respaldo para clientes sin sigla (sin conexión en vivo posible).
    estado_cuenta_oficial_url: str | None = None
    estado_cuenta_oficial_actualizado_en: datetime | None = None
    # Estado de cuenta REAL de Yuda Contable, traído en vivo por su API
    # interna (ver yuda_contable_service.py). None si el cliente no tiene
    # sigla, la conexión no está configurada, o falló al traerlo -en
    # cualquier caso, el estado_cuenta_oficial_url de arriba sigue de respaldo.
    estado_cuenta_contable: EstadoCuentaContableResponse | None = None
