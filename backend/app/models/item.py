import secrets
import uuid

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def nueva_referencia() -> str:
    """Referencia de catálogo que ve el CLIENTE en su cotización (REF-748213).

    Es un número al azar, no un consecutivo: no revela cuántos productos se han
    cotizado ni el código del proveedor. Se guarda con el ítem, así que una vez
    asignada no cambia aunque la cotización se vuelva a exportar.
    """
    return f"REF-{secrets.randbelow(900_000) + 100_000}"


class Item(Base):
    """Ítem (producto) dentro de una sesión de cotización"""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    sesion_id: Mapped[str] = mapped_column(
        String, ForeignKey("sesiones.id"), nullable=False, index=True
    )
    # Todos los campos de texto son nullable
    supplier_nombre: Mapped[str | None] = mapped_column(String, nullable=True)
    supplier_numero: Mapped[str | None] = mapped_column(String, nullable=True)
    # Foto 1: producto + tablero con datos. Es la que lee el OCR.
    foto_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Foto 2 (final/limpia): solo se muestra en los documentos del cliente y del
    # proveedor. No se extraen datos de ella. Si falta, se usa foto_url.
    foto_final_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # Referencia de YUDA para el cliente (la piden para pedir por catálogo). Se
    # asigna sola al crear el ítem y solo sale en los documentos del cliente;
    # el pedido al proveedor sigue yendo con item_no (el código del proveedor).
    referencia: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, default=nueva_referencia
    )
    item_no: Mapped[str | None] = mapped_column(String, nullable=True)
    # Marca de fabrica del producto. No sale del cartel: la escribe la vendedora.
    marca: Mapped[str | None] = mapped_column(String, nullable=True)
    # Cuando el proveedor entrego la mercancia. Se llena despues de la cotizacion.
    fecha_recibo: Mapped[str | None] = mapped_column(String, nullable=True)
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
    # Cajas (CTNS) que el CLIENTE pidió desde su portal, para el pedido al
    # proveedor. Null hasta que el cliente envíe su pedido.
    cantidad_solicitada: Mapped[int | None] = mapped_column(Integer, nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0)

    # El OCR ya lee "colores" desde siempre, pero nunca se guardaba: se agregaba
    # a la revisión y se perdía al agregar el producto. Se guarda para toda
    # cotización, no solo bolsos.
    colores: Mapped[str | None] = mapped_column(String, nullable=True)

    # Campos propios de una cotización de bolsos (sesion.tipo_cotizacion ==
    # "bolsos"). Quedan nullable y sin usar en una cotización de productos
    # varios, no hace falta separarlos en otra tabla.
    tamano: Mapped[str | None] = mapped_column(String, nullable=True)
    empaque: Mapped[str | None] = mapped_column(String, nullable=True)
    etiqueta: Mapped[str | None] = mapped_column(String, nullable=True)
    herrajes: Mapped[str | None] = mapped_column(String, nullable=True)
    riata: Mapped[str | None] = mapped_column(String, nullable=True)
    # Minimo que exige la TIENDA (no el modelo puntual): puede ser solo cajas,
    # o cajas + piezas por caja. Distinto de moq_cajas (el minimo del proveedor
    # para ese modelo especifico).
    minimo_cajas_tienda: Mapped[int | None] = mapped_column(Integer, nullable=True)
    minimo_piezas_caja_tienda: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Fotos aparte de la que lee el OCR: interior, herrajes, riata, exterior.
    # SIEMPRE la foto original tal como se subio, nunca se sobreescribe.
    # {"interior": url, "herrajes": url, "riata": url, "exterior": url}
    fotos_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Resultado de recortar/girar a mano una foto de fotos_extra, por tipo.
    # Mismo patron que foto_url/foto_final_url: si un tipo no esta acá, se usa
    # su foto en fotos_extra tal cual (sin recortar).
    fotos_extra_final: Mapped[dict | None] = mapped_column(JSON, nullable=True)
