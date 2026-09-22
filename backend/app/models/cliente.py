import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# De dónde salió el registro: uno que alguien creó a mano (el caso normal),
# o uno que entró en bloque al importar el listado de Yuda Contable. Sin
# esto, un contacto recién importado (con datos mínimos, sin vendedora real
# asignada todavía) era indistinguible de un cliente de verdad -se mezclaban
# en la misma lista sin ninguna forma de separarlos.
ORIGEN_MANUAL = "manual"
ORIGEN_IMPORTADO_CONTABLE = "importado_contable"


class Cliente(Base):
    """Cliente final de una vendedora. Tiene su propio acceso al portal."""

    __tablename__ = "clientes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    empresa: Mapped[str | None] = mapped_column(String, nullable=True)
    # NIT / identificación tributaria del cliente (aparece en el estado de cuenta).
    nit: Mapped[str | None] = mapped_column(String, nullable=True)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    pais: Mapped[str | None] = mapped_column(String, nullable=True)
    # Código corto ("sigla") con el que este cliente aparece en Yuda Contable
    # (app aparte). Es solo una etiqueta de referencia cruzada, la escribe
    # Marcela a mano; nunca se trae saldo ni movimientos de esa app.
    sigla: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    # Vendedora dueña del cliente
    vendedora_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    origen: Mapped[str] = mapped_column(
        String, default=ORIGEN_MANUAL, server_default=ORIGEN_MANUAL, nullable=False
    )
    # Versión de token para revocación (ver User.token_version).
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
