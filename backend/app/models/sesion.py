import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Estados del pedido del cliente (circuito de confirmación):
#   recibido      -> el cliente propuso cantidades desde el portal
#   por_confirmar -> la vendedora las revisó/editó y las envió a confirmar
#   confirmado    -> el cliente confirmó; recién ahí se genera el pedido al proveedor
PEDIDO_RECIBIDO = "recibido"
PEDIDO_POR_CONFIRMAR = "por_confirmar"
PEDIDO_CONFIRMADO = "confirmado"


class Sesion(Base):
    """Sesión de cotización asociada a un cliente y a un usuario"""

    __tablename__ = "sesiones"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre_cliente: Mapped[str] = mapped_column(String, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_cambio_usd: Mapped[float] = mapped_column(Float, default=6.7)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    # Cliente del portal al que está vinculada y enviada la cotización (opcional)
    cliente_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("clientes.id"), nullable=True, index=True
    )
    # Contenedor/embarque al que pertenece la cotización. Cuando está seteado, la
    # TRM del contenedor manda sobre `tipo_cambio_usd` para facturar en USD.
    contenedor_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("contenedores.id"), nullable=True, index=True
    )
    enviada_cliente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_envio_cliente: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Pedido del cliente desde el portal: notas/observaciones y cuándo lo envió.
    notas_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)
    pedido_recibido_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Estado del circuito de confirmación (recibido / por_confirmar / confirmado)
    pedido_estado: Mapped[str | None] = mapped_column(String, nullable=True)
    pedido_confirmado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
