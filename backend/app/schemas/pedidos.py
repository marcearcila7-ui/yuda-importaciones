from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PedidoGeneradoInfo(BaseModel):
    """Información de un pedido generado para devolver al frontend"""

    supplier: str
    archivo_nombre: str
    url_descarga: str
    url_pdf: str | None = None
    items_count: int


class GenerarPedidosResponse(BaseModel):
    """Resultado de generar pedidos: lista de pedidos y advertencias"""

    pedidos: list[PedidoGeneradoInfo]
    warnings: list[str]


class PedidoGeneradoResponse(BaseModel):
    """Registro persistido de un pedido generado"""

    id: str
    sesion_id: str
    supplier: str
    archivo_xlsx_url: str
    archivo_pdf_url: str | None = None
    archivo_csv_url: str | None = None
    archivo_real_xlsx_url: str | None = None
    archivo_real_pdf_url: str | None = None
    archivo_real_csv_url: str | None = None
    revisado_en_bodega_at: datetime | None = None
    fecha_generacion: datetime
    fecha_tentativa_entrega: date | None = None
    # Para que Marcela (super admin) vea de un vistazo quién hizo cada paso,
    # no solo que "ya se hizo". None si el pedido es de antes de este cambio.
    generado_por_nombre: str | None = None
    revisado_por_nombre: str | None = None
    # True si las cajas con las que se armaron estos archivos ya no son las
    # que están hoy en la cotización (típico: se generó el pedido y DESPUÉS
    # el cliente mandó sus cantidades desde el portal). Sin esto la vendedora
    # bajaba un Excel viejo creyendo que era el bueno.
    cantidades_desactualizadas: bool = False

    model_config = ConfigDict(from_attributes=True)


class FechaTentativaInput(BaseModel):
    fecha: date


class EnviarABodegaInput(BaseModel):
    asignado_a_id: str | None = None
