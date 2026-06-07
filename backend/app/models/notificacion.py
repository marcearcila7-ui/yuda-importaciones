import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Tipos de aviso para el equipo (por ahora solo el aviso de "listo para envío").
TIPO_LISTO_PARA_ENVIO = "listo_para_envio"


class Notificacion(Base):
    """Aviso interno dirigido a un usuario del equipo (ej. Marcela).

    Se usa para avisarle que una cotización está lista para que cargue la
    naviera y el BL. Es un aviso dentro de la app (campana + listado).
    """

    __tablename__ = "notificaciones"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    sesion_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("sesiones.id"), nullable=True
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    titulo: Mapped[str] = mapped_column(String, nullable=False)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
