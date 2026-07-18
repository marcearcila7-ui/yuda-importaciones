import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class RolUsuario(str, Enum):
    """Roles disponibles para los usuarios del sistema"""

    admin = "admin"
    vendedora = "vendedora"
    contadora = "contadora"


class User(Base):
    """Usuario del sistema"""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(SAEnum(RolUsuario), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Versión de token para revocación: al subirla se invalidan todos los JWT
    # emitidos antes (p. ej. al resetear la contraseña).
    token_version: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
