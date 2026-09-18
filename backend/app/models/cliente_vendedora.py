import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ClienteVendedora(Base):
    """Vendedora adicional con acceso a un cliente, más allá de la dueña
    original (Cliente.vendedora_id). Un cliente puede quedar compartido entre
    varias vendedoras; Marcela es quien asigna."""

    __tablename__ = "cliente_vendedoras"
    __table_args__ = (UniqueConstraint("cliente_id", "vendedora_id", name="uq_cliente_vendedora"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cliente_id: Mapped[str] = mapped_column(String, ForeignKey("clientes.id"), nullable=False, index=True)
    vendedora_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, index=True)
    asignado_por_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ClienteActividad(Base):
    """Nota libre de actividad sobre un cliente (llamadas, acuerdos, cambios),
    dejada por cualquier vendedora con acceso o por Marcela. Es la bitácora
    que permite ver qué hizo cada una cuando el cliente es compartido."""

    __tablename__ = "cliente_actividad"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cliente_id: Mapped[str] = mapped_column(String, ForeignKey("clientes.id"), nullable=False, index=True)
    usuario_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    nota: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
