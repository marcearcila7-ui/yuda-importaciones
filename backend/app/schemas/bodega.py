from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.cubicaje import SobranteListaItem
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
    # Quién de bodega lo tiene asignado (None = sin asignar, lo ven todos).
    bodega_asignado_a_id: str | None = None
    bodega_asignado_a_nombre: str | None = None
    # Solo se llena en la vista "listas_sobrantes": qué referencias y cuántas
    # cajas quedaron sobrando en este pedido.
    sobrante_items: list[SobranteListaItem] | None = None


class UsuarioBodegaBasico(BaseModel):
    """Para el selector de a quién asignar: cualquier admin o bodega activo."""

    id: str
    nombre: str


class AsignarPedidoInput(BaseModel):
    asignado_a_id: str | None = None


class ActividadBodegaResponse(BaseModel):
    usuario_nombre: str | None = None
    tipo: str
    detalle: str | None = None
    created_at: datetime


class PedidoBodegaSeguimientoResumen(BaseModel):
    """Para el panel de la vendedora: control de todo lo que se envió a
    bodega, sin importar quién de sus clientes sea."""

    sesion_id: str
    numero: str
    cliente_nombre: str
    fecha: date
    estado_envio: str
    total_ordenes: int
    ordenes_revisadas: int
    bodega_asignado_a_id: str | None = None
    bodega_asignado_a_nombre: str | None = None
    actividad_reciente: list[ActividadBodegaResponse] = []


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
    cliente_email: str | None = None
    cliente_telefono: str | None = None
    # El WhatsApp del cliente se hereda de Yuda Contable (por "sigla"): ni
    # bodega ni la vendedora lo editan acá, solo lo ven. Si hace falta
    # corregirlo, se edita en la ficha del cliente en Yuda Contable y este
    # valor se actualiza solo (ver /contacto-cliente para el polling en vivo).
    # None si no hay sigla, no hay conexión configurada, o Yuda Contable no
    # tiene nada para esa sigla.
    cliente_whatsapp_contable: str | None = None
    # Vendedora dueña de la cotización en el cotizador.
    vendedora_nombre: str | None = None
    vendedora_email: str | None = None
    bodega_asignado_a_id: str | None = None
    bodega_asignado_a_nombre: str | None = None
    actividad: list[ActividadBodegaResponse] = []


class ContactoClienteResponse(BaseModel):
    """Para el polling en vivo de la pestaña Notificaciones: el WhatsApp que
    Yuda Contable tiene registrado ahora mismo para este cliente."""

    whatsapp: str | None = None


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
