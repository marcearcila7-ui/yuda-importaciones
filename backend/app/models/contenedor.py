import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Estados posibles de un contenedor/embarque, en orden de avance.
ESTADOS_CONTENEDOR = [
    "abierto",      # Se está armando: se le asocian cotizaciones/envíos
    "en_transito",  # Salió de China rumbo a destino
    "cerrado",      # Liquidado; ya no se le agregan movimientos
]

ESTADO_INICIAL_CONTENEDOR = "abierto"


class Contenedor(Base):
    """Contenedor / embarque que agrupa cotizaciones y envíos.

    Guarda la TRM (tasa de cambio RMB→USD) fijada manualmente por la contadora
    para ese embarque. Esa tasa es la fuente de verdad para convertir precios en
    RMB a USD en facturas y cuentas de clientes; `Sesion.tipo_cambio_usd` queda
    como respaldo cuando la cotización no está asociada a un contenedor.
    """

    __tablename__ = "contenedores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # Código o nombre del contenedor (ej: "YUDA-2026-07"). No único: puede repetirse año a año.
    codigo: Mapped[str] = mapped_column(String, nullable=False, index=True)
    # TRM manual: cuántos RMB equivalen a 1 USD para este embarque.
    trm_usd: Mapped[float] = mapped_column(Float, default=6.7, nullable=False)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String, default=ESTADO_INICIAL_CONTENEDOR, nullable=False)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
