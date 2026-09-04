from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ItemCreate(BaseModel):
    """Datos crudos para crear un ítem del packing list"""

    supplier_nombre: Optional[str] = None
    supplier_numero: Optional[str] = None
    foto_url: Optional[str] = None
    # Foto final (limpia) para los documentos de cliente/proveedor; si falta se usa foto_url.
    foto_final_url: Optional[str] = None
    item_no: Optional[str] = None
    descripcion_es: Optional[str] = None
    descripcion_en: Optional[str] = None
    descripcion_zh: Optional[str] = None
    material: Optional[str] = None
    uso: Optional[str] = None
    qty_por_ctn: int = 1
    price_rmb: float = 0.0
    gw: float = 0.0
    largo_cm: float = 0.0
    ancho_cm: float = 0.0
    alto_cm: float = 0.0
    # CBM directo de etiqueta (opcional); si es None se calcula por dimensiones.
    cbm: Optional[float] = None
    # MQT: mínima cantidad de cajas que pide el proveedor.
    moq_cajas: Optional[int] = None
    ctns: int = 1
    orden: int = 0


class RecorteRequest(BaseModel):
    """Recuadro para recortar a mano la foto de un producto.

    [x0, y0, x1, y1] en fracciones de 0 a 1. En null se descarta el recorte y los
    documentos vuelven a usar la foto completa.
    """

    recuadro: Optional[list[float]] = None


class ItemUpdate(BaseModel):
    """Campos opcionales para actualización parcial (PATCH) de un ítem"""

    supplier_nombre: Optional[str] = None
    supplier_numero: Optional[str] = None
    foto_final_url: Optional[str] = None
    item_no: Optional[str] = None
    descripcion_es: Optional[str] = None
    descripcion_en: Optional[str] = None
    descripcion_zh: Optional[str] = None
    material: Optional[str] = None
    uso: Optional[str] = None
    qty_por_ctn: Optional[int] = None
    price_rmb: Optional[float] = None
    gw: Optional[float] = None
    largo_cm: Optional[float] = None
    ancho_cm: Optional[float] = None
    alto_cm: Optional[float] = None
    cbm: Optional[float] = None
    moq_cajas: Optional[int] = None
    ctns: Optional[int] = None
    orden: Optional[int] = None


class ItemResponse(ItemCreate):
    """Ítem completo con sus campos calculados (no almacenados en DB)"""

    id: str
    sesion_id: str
    foto_url: Optional[str] = None
    referencia: Optional[str] = None  # referencia de catálogo (documentos del cliente)
    cantidad_solicitada: Optional[int] = None  # cajas que pidió el cliente en su portal
    t_qty: int
    total_rmb: float
    price_usd: float
    total_usd: float
    cbm: float
    t_cbm: float
    t_gw: float

    model_config = ConfigDict(from_attributes=True)


class SesionCreate(BaseModel):
    """Datos para crear una sesión de cotización"""

    nombre_cliente: str
    tipo_cambio_usd: float = 6.7
    # Si se crea para un cliente del portal, su id (la cotización nace vinculada)
    cliente_id: str | None = None


class SesionResponse(BaseModel):
    """Sesión de cotización"""

    id: str
    nombre_cliente: str
    fecha: date
    tipo_cambio_usd: float
    user_id: str
    cliente_id: str | None = None
    contenedor_id: str | None = None  # embarque al que pertenece (define la TRM al facturar)
    enviada_cliente: bool = False
    notas_cliente: str | None = None  # observaciones que dejó el cliente en su pedido
    pedido_recibido_at: datetime | None = None  # cuándo el cliente envió su pedido
    pedido_estado: str | None = None  # recibido / por_confirmar / confirmado
    pedido_confirmado_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReordenarItem(BaseModel):
    """Par id/orden para reordenar ítems"""

    id: str
    orden: int


class CantidadClienteLinea(BaseModel):
    """Cajas que se piden de un producto (cantidad final del cliente)"""

    item_id: str
    cantidad: int


class EnviarAConfirmarInput(BaseModel):
    """La vendedora ajusta las cantidades y las envía al cliente a confirmar"""

    items: list[CantidadClienteLinea]
