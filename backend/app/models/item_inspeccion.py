import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class ItemInspeccionBodega(Base):
    """Corrección de bodega sobre un ítem de la cotización del cliente, hecha al
    inspeccionar físicamente lo que llegó del proveedor.

    Todos los campos son overrides opcionales: si están en None, se usa el
    valor original del Item (el que cargó la vendedora al cotizar). Esta tabla
    es aparte a propósito: el portal del cliente lee directo de Item y nunca
    de acá, así que lo que bodega corrige no le llega al cliente -solo a la
    vendedora, que ve la cotización con estas correcciones fusionadas."""

    __tablename__ = "item_inspeccion_bodega"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_id: Mapped[str] = mapped_column(
        String, ForeignKey("items.id"), nullable=False, unique=True, index=True
    )

    referencia: Mapped[str | None] = mapped_column(String, nullable=True)
    item_no: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion_es: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion_en: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion_zh: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    uso: Mapped[str | None] = mapped_column(String, nullable=True)
    marca: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_recibo: Mapped[str | None] = mapped_column(String, nullable=True)

    # Cantidades y medidas reales, contadas/medidas por bodega. A veces llegan
    # más cajas de las que se cotizaron, o con otras medidas/peso.
    ctns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qty_por_ctn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_rmb: Mapped[float | None] = mapped_column(Float, nullable=True)
    largo_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    ancho_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    alto_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    gw: Mapped[float | None] = mapped_column(Float, nullable=True)
    moq_cajas: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Propios de bolsos (sesion.tipo_cotizacion == "bolsos")
    tamano: Mapped[str | None] = mapped_column(String, nullable=True)
    empaque: Mapped[str | None] = mapped_column(String, nullable=True)
    etiqueta: Mapped[str | None] = mapped_column(String, nullable=True)
    herrajes: Mapped[str | None] = mapped_column(String, nullable=True)
    riata: Mapped[str | None] = mapped_column(String, nullable=True)
    minimo_cajas_tienda: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimo_piezas_caja_tienda: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # None = todavía sin revisar; True/False = bodega confirmó si el producto
    # físico coincide con la referencia de la cotización original.
    referencia_coincide: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Evidencia de la inspección: hasta 4 fotos y 1 video. Aparte de
    # fotos_extra/foto_final_url del Item (esas SÍ se ven en los documentos del
    # cliente; estas nunca).
    fotos: Mapped[list | None] = mapped_column(JSON, nullable=True)
    video_url: Mapped[str | None] = mapped_column(String, nullable=True)

    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actualizado_por_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id"), nullable=True
    )
