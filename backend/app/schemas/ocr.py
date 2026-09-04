from typing import Optional

from pydantic import BaseModel


class OCRResultado(BaseModel):
    """Datos extraídos de una etiqueta de proveedor"""

    supplier_nombre: Optional[str] = None
    supplier_numero: Optional[str] = None
    price_rmb: Optional[float] = None
    qty_por_ctn: Optional[int] = None
    largo_cm: Optional[float] = None
    ancho_cm: Optional[float] = None
    alto_cm: Optional[float] = None
    cbm_directo: Optional[float] = None
    colores: Optional[str] = None
    cantidad_minima: Optional[int] = None
    # Mínimo para comprarle a la tienda en total; solo viene cuando el cartel
    # trae los dos mínimos y la vendedora elige cuál usar.
    cantidad_minima_tienda: Optional[int] = None
    descripcion_zh: Optional[str] = None
    notas: Optional[str] = None
    confianza: str = "baja"
    # Calidad de la foto: si es False, la vendedora debe volver a tomarla
    legible: bool = True
    motivo_ilegible: Optional[str] = None


class OCRResponse(BaseModel):
    """Respuesta del endpoint de OCR: URL de la foto y datos extraídos"""

    foto_url: str
    datos_extraidos: OCRResultado
