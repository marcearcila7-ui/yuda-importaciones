from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.pedidos import PedidoGeneradoResponse
from app.schemas.portal import PortalItem
from app.schemas.seguimiento import SeguimientoResponse


class BodegaPedidoResumen(BaseModel):
    """Fila de la cola de bodega: un pedido confirmado listo para revisar"""

    sesion_id: str
    numero: str
    nombre_cliente: str
    fecha: date
    total_items: int
    # Cuántas órdenes a proveedor tiene esta cotización, y cuántas ya revisó
    # bodega (con las cantidades reales guardadas).
    total_ordenes: int
    ordenes_revisadas: int
    pedido_confirmado_at: datetime | None = None
    estado_envio: str
    # Vendedora dueña de la cotización en el cotizador (a quién preguntarle si
    # algo no cuadra).
    vendedora_nombre: str | None = None


class BodegaPedidoDetalle(BaseModel):
    """Detalle que bodega usa para comparar el pedido contra la orden de compra"""

    sesion_id: str
    numero: str
    nombre_cliente: str
    fecha: date
    items: list[PortalItem]
    notas_cliente: str | None = None
    pedidos_generados: list[PedidoGeneradoResponse]
    seguimiento: SeguimientoResponse
    # Datos del cliente del portal (a quien se le avisa por correo/WhatsApp al
    # marcar "en bodega"). None si esta cotización no está vinculada a un cliente.
    cliente_nombre: str | None = None
    cliente_telefono: str | None = None
    # Vendedora dueña de la cotización en el cotizador.
    vendedora_nombre: str | None = None
    vendedora_email: str | None = None


class ActualizarTelefonoInput(BaseModel):
    telefono: str


class OrdenGeneradaItem(BaseModel):
    """Una línea de la orden a un proveedor: lo pedido vs. lo que bodega contó."""

    item_id: str
    referencia: str | None = None
    descripcion_es: str | None = None
    descripcion_en: str | None = None
    foto_url: str | None = None
    qty_por_ctn: int = 0
    cantidad_pedida: int
    cantidad_recibida: int | None = None
    nota: str | None = None


class OrdenGenerada(BaseModel):
    """La orden completa a un proveedor (antes "PedidoGenerado"), con sus líneas
    para que bodega compare y corrija."""

    pedido_generado_id: str
    supplier: str
    fecha_generacion: datetime
    archivo_xlsx_url: str
    archivo_pdf_url: str | None = None
    archivo_csv_url: str | None = None
    archivo_real_xlsx_url: str | None = None
    archivo_real_pdf_url: str | None = None
    archivo_real_csv_url: str | None = None
    revisado_en_bodega_at: datetime | None = None
    items: list[OrdenGeneradaItem]


class OrdenGeneradaItemInput(BaseModel):
    item_id: str
    cantidad_recibida: int
    nota: str | None = None


class GuardarOrdenRealInput(BaseModel):
    items: list[OrdenGeneradaItemInput]
