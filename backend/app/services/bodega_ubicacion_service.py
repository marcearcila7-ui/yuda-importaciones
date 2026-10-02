"""En qué parte de la cola de bodega está un pedido, o por qué no está.

Vive aparte porque lo necesitan dos sitios que no se pueden importar entre
sí: el endpoint de bodega que lo devuelve a la cola, y la respuesta de
seguimiento que ve Marcela en el cotizador.
"""
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.seguimiento import SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User


def donde_esta_en_bodega(db: Session, seg: SeguimientoPedido) -> str:
    """En cuál de las cinco pestañas de bodega cae este pedido ahora mismo, o
    por qué no cae en ninguna.

    Las pestañas no son un filtro libre: cada una exige una etapa concreta
    (ver listar_pedidos), así que un pedido puede estar perfectamente en la
    cola y aun así no verse en la pestaña que uno está mirando. Y hay dos
    filtros que lo sacan de TODAS sin decir nada: que el cliente esté
    desactivado y que la cotización esté archivada. Eso es lo peor de buscar
    un pedido "perdido", así que se nombra explícitamente."""
    sesion = db.query(Sesion).filter(Sesion.id == seg.sesion_id).first()
    if sesion is not None:
        if sesion.archivada_en is not None:
            return "ninguna: esta cotización está archivada, por eso bodega no la ve"
        cliente = (
            db.query(Cliente).filter(Cliente.id == sesion.cliente_id).first()
            if sesion.cliente_id
            else None
        )
        if sesion.cliente_id is None:
            return "ninguna: es una cotización libre, sin cliente asociado"
        if cliente is None or not cliente.activo:
            return "ninguna: el cliente está desactivado, por eso bodega no lo ve"

    if seg.cliente_aprobo_despacho_at is not None or seg.estado in ("en_transito", "en_destino", "entregado"):
        return "Completados"
    if seg.estado == "en_bodega":
        return "Pendiente por aprobación del cliente"
    if seg.estado == "proveedor_recibio":
        if seg.bodega_asignado_a_id:
            asignado = db.query(User).filter(User.id == seg.bodega_asignado_a_id).first()
            return f"Asignados, a nombre de {asignado.nombre}" if asignado else "Asignados"
        return "Sin asignar"
    # Antes de "proveedor recibió" el pedido todavía no se le avisó a bodega.
    return "todavía sin avisar a bodega"
