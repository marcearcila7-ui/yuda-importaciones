import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Porcentaje del depósito inicial y del saldo de un pedido a tienda.
PCT_DEPOSITO = 0.30
PCT_SALDO = 0.70
# Días antes de la fecha estimada de pago del 70% en que se avisa a la contadora.
DIAS_AVISO_PAGO_70 = 7

# Estados derivados (no se almacenan).
ESTADO_PENDIENTE = "pendiente"
ESTADO_PARCIAL = "parcial"
ESTADO_PAGADO = "pagado"


class PedidoTienda(Base):
    """Pedido a una tienda en China con su esquema de pago 30/70.

    Montos en CNY (yuanes). El 30%, el 70% y la comisión se calculan a partir del
    total y no se almacenan. La contadora fija la fecha estimada de pago del 70%,
    que dispara el aviso in-app cuando se acerca.
    """

    __tablename__ = "pedidos_tienda"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre_tienda: Mapped[str] = mapped_column(String, nullable=False)
    fecha_pedido: Mapped[date | None] = mapped_column(Date, nullable=True)
    monto_total: Mapped[float] = mapped_column(Numeric(12, 2), default=0, nullable=False)

    # 30% depósito
    fecha_pago_30: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Entrega de la tienda (~20 días)
    fecha_estimada_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_real_entrega: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 70% saldo: la contadora fija la fecha estimada; el aviso se dispara cerca de ella.
    fecha_estimada_pago_70: Mapped[date | None] = mapped_column(Date, nullable=True)
    fecha_pago_70: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Comisión que la tienda da a YUDA sobre este pedido (0 si no da).
    pct_comision_tienda: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    # Fecha en que YUDA recibió la comisión (para totalizar por período).
    fecha_comision: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Empleada que gestionó la compra (para el ranking).
    empleada_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True, index=True
    )
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
