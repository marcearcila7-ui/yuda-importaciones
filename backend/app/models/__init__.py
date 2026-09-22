# Reexporta todos los modelos para que Base.metadata los registre (Alembic)
from app.models.user import User
from app.models.sesion import Sesion
from app.models.item import Item
from app.models.pedido import PedidoGenerado
from app.models.notificacion import Notificacion
from app.models.contenedor import Contenedor
from app.models.cuenta import MovimientoCuenta
from app.models.tienda import PedidoTienda
from app.models.cliente import Cliente
from app.models.cliente_vendedora import ClienteVendedora, ClienteActividad
from app.models.item_inspeccion import ItemInspeccionBodega
from app.models.pedido_bodega_actividad import PedidoBodegaActividad
from app.models.cubicaje import CubicajeMensaje

__all__ = [
    "User",
    "Sesion",
    "Item",
    "PedidoGenerado",
    "Notificacion",
    "Contenedor",
    "MovimientoCuenta",
    "PedidoTienda",
    "Cliente",
    "ClienteVendedora",
    "ClienteActividad",
]
