import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class LoteOCR(Base):
    """Trabajo de carga masiva de fotos para una sesión"""

    __tablename__ = "lotes_ocr"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(String, ForeignKey("sesiones.id"), nullable=False)
    # cargando -> procesando -> completado
    estado: Mapped[str] = mapped_column(String, default="cargando", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoteItem(Base):
    """Cada foto de un lote, con su resultado de OCR"""

    __tablename__ = "lote_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    lote_id: Mapped[str] = mapped_column(String, ForeignKey("lotes_ocr.id"), nullable=False)
    foto_url: Mapped[str] = mapped_column(String, nullable=False)
    # pendiente -> ok | error
    estado: Mapped[str] = mapped_column(String, default="pendiente", nullable=False)
    datos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
