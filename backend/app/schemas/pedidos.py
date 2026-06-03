from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PedidoGeneradoInfo(BaseModel):
    """Información de un pedido generado para devolver al frontend"""

    supplier: str
    archivo_nombre: str
    url_descarga: str
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
    fecha_generacion: datetime

    model_config = ConfigDict(from_attributes=True)
