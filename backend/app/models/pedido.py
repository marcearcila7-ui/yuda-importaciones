import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PedidoGenerado(Base):
    """Pedido (archivo de compra) generado a partir de una sesión"""

    __tablename__ = "pedidos_generados"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(String, ForeignKey("sesiones.id"), nullable=False)
    supplier: Mapped[str] = mapped_column(String, nullable=False)
    archivo_xlsx_url: Mapped[str] = mapped_column(String, nullable=False)
    archivo_pdf_url: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
