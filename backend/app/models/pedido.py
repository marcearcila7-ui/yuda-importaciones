import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class PedidoGenerado(Base):
    """Pedido (archivo de compra) generado a partir de una sesión, agrupado por
    proveedor/tienda. Se genera con lo que confirmó el cliente; bodega, al
    recibir la mercancía, puede corregirlo con lo que realmente llegó (ver
    PedidoGeneradoItem) y eso regenera una segunda versión "real" de los
    mismos archivos."""

    __tablename__ = "pedidos_generados"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(String, ForeignKey("sesiones.id"), nullable=False)
    supplier: Mapped[str] = mapped_column(String, nullable=False)
    # Lo que se pidió (se genera al confirmar el cliente).
    archivo_xlsx_url: Mapped[str] = mapped_column(String, nullable=False)
    archivo_pdf_url: Mapped[str | None] = mapped_column(String, nullable=True)
    archivo_csv_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Lo que realmente llegó (bodega lo genera al guardar sus correcciones).
    archivo_real_xlsx_url: Mapped[str | None] = mapped_column(String, nullable=True)
    archivo_real_pdf_url: Mapped[str | None] = mapped_column(String, nullable=True)
    archivo_real_csv_url: Mapped[str | None] = mapped_column(String, nullable=True)
    revisado_en_bodega_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fecha_generacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PedidoGeneradoItem(Base):
    """Una línea de un PedidoGenerado: cuánto se pidió de ese ítem a ese
    proveedor, y cuánto llegó realmente según bodega (null hasta que bodega
    lo revisa)."""

    __tablename__ = "pedido_generado_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    pedido_generado_id: Mapped[str] = mapped_column(
        String, ForeignKey("pedidos_generados.id"), nullable=False, index=True
    )
    item_id: Mapped[str] = mapped_column(String, ForeignKey("items.id"), nullable=False, index=True)
    # Cajas pedidas, tal como quedaron en el archivo enviado al proveedor.
    cantidad_pedida: Mapped[int] = mapped_column(Integer, nullable=False)
    # Cajas que bodega cuenta al recibir; null hasta que bodega guarda su revisión.
    cantidad_recibida: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
