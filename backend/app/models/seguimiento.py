import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, Text
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

# Etapas que la vendedora puede gestionar. De "en_transito" en adelante (cuando
# el contenedor ya está en camino) la información es exclusiva de Marcela (admin).
ESTADOS_VENDEDORA = [
    "cotizacion_enviada",
    "pedido_confirmado",
    "proveedor_recibio",
    "en_bodega",
]

# Campos de envío que solo Marcela (admin) puede editar.
CAMPOS_SOLO_ADMIN = ("numero_tracking", "naviera", "url_tracking", "bl_numero", "bl_pdf_url")

# Etapa que dispara el aviso a Marcela: la mercancía está lista para enviarse,
# es el momento de cargar naviera y BL.
ESTADO_DISPARA_AVISO = "en_bodega"


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
    # BL (Bill of Lading): lo carga Marcela cuando el contenedor está en tránsito.
    bl_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    bl_pdf_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Monto de la venta en USD, que Marcela ingresa al despachar (obligatorio al
    # pasar a "en tránsito"). Alimenta el panel de ventas del dashboard.
    monto_venta: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Sello de cuándo el pedido pasó a "en tránsito" (despacho del contenedor),
    # para filtrar las ventas por fecha en el panel de Marcela.
    despachado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    # { estado_key: { "fecha": "YYYY-MM-DD", "nota": "..." } }
    hitos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
