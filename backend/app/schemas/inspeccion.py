"""Cotización del cliente editable por bodega: cada campo trae el valor
original (el que cargó la vendedora) y el corregido (lo que bodega guardó,
si acaso). El front decide qué mostrar; el backend nunca decide "cuál gana"
más allá de servir ambos valores."""
from datetime import date, datetime

from pydantic import BaseModel


class CampoInspeccion(BaseModel):
    original: str | float | int | None = None
    corregido: str | float | int | None = None


class CajaExtra(BaseModel):
    """Una caja fuera de lo uniforme (ej. la mayoría trae 100 uds/caja pero
    llegó una con 50, o con medidas/peso distintos). Se suma a `cajas` del
    ítem, no lo reemplaza: `cajas`/`uds_caja`/medidas siguen siendo la caja
    "normal", esto son las que hay que anotar aparte."""
    ctns: int
    qty_por_ctn: int
    largo_cm: float | None = None
    ancho_cm: float | None = None
    alto_cm: float | None = None
    gw: float | None = None


class InspeccionItemResponse(BaseModel):
    item_id: str
    foto_url: str | None = None
    foto_final_url: str | None = None
    # Tienda/proveedor de este producto: PedidoGenerado.supplier se arma como
    # f"{supplier_nombre}_{supplier_numero}" (ver agrupar_items_por_supplier),
    # así que hacen falta los dos para reconstruir esa misma clave y agrupar
    # los productos bajo la orden a la que pertenecen.
    supplier_nombre: str | None = None
    supplier_numero: str | None = None

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
    cajas_extra: list[CajaExtra] = []
    # Bodega confirma a propósito que no hay cajas fuera de lo uniforme que
    # reportar (no es lo mismo que "todavía no lo revisó"): sin este campo
    # aparte, una lista vacía no distingue "nada que reportar" de "nunca lo
    # miró".
    sin_cajas_extra: bool = False
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
    cajas_extra: list[CajaExtra] | None = None
    sin_cajas_extra: bool = False


class GuardarInspeccionInput(BaseModel):
    shipping_mark: str | None = None
    items: list[InspeccionItemInput]
