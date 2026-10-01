import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Estatus de una tarea de pago.
ESTATUS_PAGADO = "pagado"
ESTATUS_NO_PAGADO = "no_pagado"
ESTATUS_APLAZADO = "aplazado"


class PagoTarea(Base):
    """Una tarea de pago del calendario del área contable: a qué tienda se le
    paga, de qué cliente/marca, cuánto (en RMB) y en qué estatus. A
    diferencia del calendario de bodega, no es texto libre -son casillas
    fijas que siempre son las mismas. Cualquiera de admin/contadora puede
    crear y editar cualquier pago (no es "de un dueño"), pero queda
    registrado quién lo creó y quién lo editó por última vez (incluido
    moverlo de día, que es una edición más)."""

    __tablename__ = "pagos_tareas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    tienda: Mapped[str] = mapped_column(String, nullable=False)
    cliente_id: Mapped[str] = mapped_column(String, ForeignKey("clientes.id"), nullable=False)
    # Sigla del cliente al momento de guardar (denormalizado, mismo criterio
    # que creado_por_nombre): evita un join contra `clientes` en cada
    # listado del calendario.
    cliente_sigla: Mapped[str] = mapped_column(String, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    estatus: Mapped[str] = mapped_column(String, nullable=False, default=ESTATUS_NO_PAGADO)

    # Nullable: si se elimina el usuario que lo creó, el pago no se borra (es
    # un tablero compartido, no "de un dueño") -el id queda en null pero el
    # nombre, guardado aparte, se conserva siempre.
    creado_por_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    creado_por_nombre: Mapped[str] = mapped_column(String, nullable=False)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    actualizado_por_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
    actualizado_por_nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
