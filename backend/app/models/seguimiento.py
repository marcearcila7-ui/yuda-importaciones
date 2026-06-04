import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base

# Hitos del envío en orden, pensados para una agencia de importación China → destino.
# El cliente ve esta línea de tiempo en su portal.
ESTADOS_ENVIO = [
    "cotizacion_enviada",   # La vendedora envió la cotización al cliente
    "pedido_confirmado",    # El cliente confirmó el pedido
    "proveedor_recibio",    # El proveedor recibió el pedido
    "en_bodega",            # Mercancía recibida en bodega (lista para envío)
    "en_transito",          # En tránsito: contenedores en camino (tracking + naviera)
    "en_destino",           # Arribó al país de destino
    "entregado",            # Entregado al cliente
]

ESTADO_INICIAL = "cotizacion_enviada"


class SeguimientoPedido(Base):
    """Seguimiento del envío de una cotización (1 a 1 con la sesión)."""

    __tablename__ = "seguimientos"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(
        String, ForeignKey("sesiones.id"), unique=True, nullable=False
    )
    estado: Mapped[str] = mapped_column(String, default=ESTADO_INICIAL, nullable=False)
    novedades: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_tracking: Mapped[str | None] = mapped_column(String, nullable=True)
    naviera: Mapped[str | None] = mapped_column(String, nullable=True)
    url_tracking: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_eta: Mapped[date | None] = mapped_column(Date, nullable=True)
    # { estado_key: { "fecha": "YYYY-MM-DD", "nota": "..." } }
    hitos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
