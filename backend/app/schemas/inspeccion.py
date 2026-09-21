"""Cotización del cliente editable por bodega: cada campo trae el valor
original (el que cargó la vendedora) y el corregido (lo que bodega guardó,
si acaso). El front decide qué mostrar; el backend nunca decide "cuál gana"
más allá de servir ambos valores."""
from datetime import date, datetime

from pydantic import BaseModel


class CampoInspeccion(BaseModel):
    original: str | float | int | None = None
    corregido: str | float | int | None = None


class InspeccionItemResponse(BaseModel):
    item_id: str
    foto_url: str | None = None
    foto_final_url: str | None = None

    referencia: CampoInspeccion
    codigo: CampoInspeccion
    descripcion_es: CampoInspeccion
    descripcion_en: CampoInspeccion
    descripcion_zh: CampoInspeccion
    material: CampoInspeccion
    uso: CampoInspeccion
    marca: CampoInspeccion
    fecha_recibo: CampoInspeccion
    cajas: CampoInspeccion
    uds_caja: CampoInspeccion
    precio_rmb: CampoInspeccion
    largo_cm: CampoInspeccion
    ancho_cm: CampoInspeccion
    alto_cm: CampoInspeccion
    peso: CampoInspeccion
    mqt: CampoInspeccion
    tamano: CampoInspeccion
    empaque: CampoInspeccion
    etiqueta: CampoInspeccion
    herrajes: CampoInspeccion
    riata: CampoInspeccion
    minimo_cajas_tienda: CampoInspeccion
    minimo_piezas_caja_tienda: CampoInspeccion

    referencia_coincide: bool | None = None
    fotos: list[str] = []
    video_url: str | None = None
    actualizado_en: datetime | None = None
    actualizado_por_nombre: str | None = None


class InspeccionSesionResponse(BaseModel):
    sesion_id: str
    numero: str
    fecha: date
    tipo_cotizacion: str | None = None
    cliente_nombre: str | None = None
    vendedora_nombre: str | None = None
    vendedora_email: str | None = None
    shipping_mark: CampoInspeccion
    items: list[InspeccionItemResponse]


class InspeccionItemInput(BaseModel):
    item_id: str
    referencia: str | None = None
    codigo: str | None = None
    descripcion_es: str | None = None
    descripcion_en: str | None = None
    descripcion_zh: str | None = None
    material: str | None = None
    uso: str | None = None
    marca: str | None = None
    fecha_recibo: str | None = None
    cajas: int | None = None
    uds_caja: int | None = None
    precio_rmb: float | None = None
    largo_cm: float | None = None
    ancho_cm: float | None = None
    alto_cm: float | None = None
    peso: float | None = None
    mqt: int | None = None
    tamano: str | None = None
    empaque: str | None = None
    etiqueta: str | None = None
    herrajes: str | None = None
    riata: str | None = None
    minimo_cajas_tienda: int | None = None
    minimo_piezas_caja_tienda: int | None = None
    referencia_coincide: bool | None = None


class GuardarInspeccionInput(BaseModel):
    shipping_mark: str | None = None
    items: list[InspeccionItemInput]
