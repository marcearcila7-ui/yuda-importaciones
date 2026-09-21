import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PedidoBodegaActividad(Base):
    """Bitácora de lo que pasa con un pedido una vez llega a bodega: quién lo
    asignó/reasignó, quién guardó cantidades reales de qué proveedor, quién
    corrigió la inspección, quién lo marcó como enviado. Con varias personas
    trabajando el mismo pedido, esto es lo que evita que se pisen sin saber
    qué hizo el otro."""

    __tablename__ = "pedido_bodega_actividad"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(
        String, ForeignKey("sesiones.id"), nullable=False, index=True
    )
    usuario_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
