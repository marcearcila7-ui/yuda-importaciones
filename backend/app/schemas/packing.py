from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ItemCreate(BaseModel):
    """Datos crudos para crear un ítem del packing list"""

    supplier_nombre: Optional[str] = None
    supplier_numero: Optional[str] = None
    foto_url: Optional[str] = None
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
    ctns: int = 1
    orden: int = 0


class ItemUpdate(BaseModel):
    """Campos opcionales para actualización parcial (PATCH) de un ítem"""

    supplier_nombre: Optional[str] = None
    supplier_numero: Optional[str] = None
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
    ctns: Optional[int] = None
    orden: Optional[int] = None


class ItemResponse(ItemCreate):
    """Ítem completo con sus campos calculados (no almacenados en DB)"""

    id: str
    sesion_id: str
    foto_url: Optional[str] = None
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
    enviada_cliente: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReordenarItem(BaseModel):
    """Par id/orden para reordenar ítems"""

    id: str
    orden: int
