import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Tipo de movimiento de bodega que registra la tarea.
TIPO_RECIBE = "recibe"
TIPO_CARGA = "carga"

# Tipo de aviso en CalendarioNotificacion (separado de Notificacion: este
# calendario tiene su propia campanita, no se mezcla con las otras apps).
TIPO_TAREA_CREADA = "creada"
TIPO_TAREA_ACTUALIZADA = "actualizada"


class CalendarioTarea(Base):
    """Una entrada libre del calendario de bodega: qué se recibe o se carga,
    de qué cliente/marca, en qué día. Cualquiera de admin/vendedora/bodega
    puede crear y editar cualquier tarea (no es "de un dueño"), pero queda
    registrado quién la creó y quién la editó por última vez."""

    __tablename__ = "calendario_tareas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    marca_cliente: Mapped[str] = mapped_column(String, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

    creado_por_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    creado_por_nombre: Mapped[str] = mapped_column(String, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Se sobreescriben en cada edición: solo se guarda la última, no un
    # historial completo (decisión explícita para la v1 de esta app).
    actualizado_por_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    actualizado_por_nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CalendarioNotificacion(Base):
    """Aviso propio de esta app (no la campanita del cotizador ni la de Yuda
    Logistic): cada app del ecosistema YUDA maneja sus propias notificaciones
    por separado."""

    __tablename__ = "calendario_notificaciones"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    tarea_id: Mapped[str] = mapped_column(
        String, ForeignKey("calendario_tareas.id"), nullable=False, index=True
    )
    tipo: Mapped[str] = mapped_column(String, nullable=False)
    titulo: Mapped[str] = mapped_column(String, nullable=False)
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
