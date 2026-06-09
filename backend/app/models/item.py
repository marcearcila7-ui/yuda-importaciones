import uuid

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Item(Base):
    """Ítem (producto) dentro de una sesión de cotización"""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(String, ForeignKey("sesiones.id"), nullable=False)
    # Todos los campos de texto son nullable
    supplier_nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    supplier_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    # Foto 1: producto + tablero con datos. Es la que lee el OCR.
    foto_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Foto 2 (final/limpia): solo se muestra en los documentos del cliente y del
    # proveedor. No se extraen datos de ella. Si falta, se usa foto_url.
    foto_final_url: Mapped[str | None] = mapped_column(String, nullable=True)
    item_no: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion_es: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion_en: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion_zh: Mapped[str | None] = mapped_column(String, nullable=True)
    material: Mapped[str | None] = mapped_column(String, nullable=True)
    uso: Mapped[str | None] = mapped_column(String, nullable=True)
    # Campos numéricos con sus valores por defecto
    qty_por_ctn: Mapped[int] = mapped_column(Integer, default=1)
    price_rmb: Mapped[float] = mapped_column(Float, default=0)
    gw: Mapped[float] = mapped_column(Float, default=0)
    largo_cm: Mapped[float] = mapped_column(Float, default=0)
    ancho_cm: Mapped[float] = mapped_column(Float, default=0)
    alto_cm: Mapped[float] = mapped_column(Float, default=0)
    # CBM leído directo de la etiqueta (si la trae). Si es None se calcula por dimensiones.
    cbm: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MQT: mínima cantidad de CAJAS que exige el proveedor (MOQ en cartones).
    moq_cajas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ctns: Mapped[int] = mapped_column(Integer, default=1)
    orden: Mapped[int] = mapped_column(Integer, default=0)
