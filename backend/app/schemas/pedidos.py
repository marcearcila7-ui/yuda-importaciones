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

    model_config = ConfigDict(from_attributes=True)


class FechaTentativaInput(BaseModel):
    fecha: date


class EnviarABodegaInput(BaseModel):
    asignado_a_id: str | None = None
