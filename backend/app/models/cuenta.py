import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Comisión de YUDA sobre el valor de la mercancía (la "logística 5%" del Excel de
# Marcela). Se aplica por defecto al crear un movimiento; puede sobrescribirse.
COMISION_YUDA_PCT = 0.05

# Monedas en las que se le puede cobrar al cliente (por pedido). Sin conversión:
# los montos se registran y se muestran en la moneda elegida.
MONEDAS = ("USD", "COP", "RMB", "EUR")

# Monedas en las que el cliente puede abonar. USDT entra aparte porque en la
# practica se recibe y se anota distinto del dolar bancario.
MONEDAS_ORIGEN = ("USD", "USDT", "COP", "RMB", "EUR")


def convertir_abono(monto_origen: float | None, tasa: float | None) -> float | None:
    """Abono en la moneda de la cuenta = monto que entro x tasa del dia.

    Devuelve None si falta alguno de los dos: ahi el abono se toma tal cual lo
    escribieron, que es como funcionaba antes de guardar la moneda de origen.
    """
    if monto_origen is None or tasa is None:
        return None
    return round(float(monto_origen) * float(tasa), 2)
MONEDA_DEFAULT = "USD"


def calcular_comision(valor_mercancia: float, pct: float = COMISION_YUDA_PCT) -> float:
    """Comisión YUDA = valor de la mercancía × porcentaje (5% por defecto)."""
    return round((valor_mercancia or 0) * pct, 2)


class MovimientoCuenta(Base):
    """Movimiento del estado de cuenta de un cliente (una fila del libro por
    cliente/contenedor de Marcela): un envío con su valor, comisión, abono y nota.

    El SALDO no se almacena: es acumulado y se calcula al leer la cuenta.
    """

    __tablename__ = "movimientos_cuenta"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cliente_id: Mapped[str] = mapped_column(
        String, ForeignKey("clientes.id"), nullable=False, index=True
    )
    # Pedido (cotización) al que pertenece el movimiento. Cada pedido lleva su
    # propia contabilidad; los movimientos sin pedido caen en un apartado aparte.
    sesion_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("sesiones.id"), nullable=True, index=True
    )
    # Contenedor/embarque al que pertenece el movimiento (opcional).
    contenedor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("contenedores.id"), nullable=True, index=True
    )
    # Identificador del envío dentro del libro (columna ENVIO del Excel).
    envio: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    guia: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(String, nullable=True)
    # Moneda de cobro del pedido (USD/COP/RMB/EUR). Los movimientos de un mismo
    # pedido comparten moneda; no hay conversión, se muestra tal cual se registra.
    moneda: Mapped[str] = mapped_column(String, default=MONEDA_DEFAULT, nullable=False)
    valor_mercancia: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    comision_yuda: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    abono: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    # De donde salio ese abono. El cliente paga en dolares o USDT y la cuenta se
    # lleva en otra moneda: guardar solo el resultado borraba el rastro de cuanto
    # entro y a que tasa, que es justo lo que se revisa cuando algo no cuadra.
    monto_origen: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    moneda_origen: Mapped[str | None] = mapped_column(String, nullable=True)
    tasa_cambio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
