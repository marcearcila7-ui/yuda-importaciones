import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class Sesion(Base):
    """Sesión de cotización asociada a un cliente y a un usuario"""

    __tablename__ = "sesiones"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre_cliente: Mapped[str] = mapped_column(String, nullable=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    tipo_cambio_usd: Mapped[float] = mapped_column(Float, default=6.7)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    # Cliente del portal al que está vinculada y enviada la cotización (opcional)
    cliente_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("clientes.id"), nullable=True
    )
    enviada_cliente: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fecha_envio_cliente: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
