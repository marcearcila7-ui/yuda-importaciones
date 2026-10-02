"""Reiniciar la revisión de bodega: deja todo como si nunca hubiera
empezado, sin tocar la cotización del cliente ni los archivos del pedido a
las tiendas. Es destructivo, así que solo Marcela y solo mientras el pedido
no haya salido de bodega.
"""
from datetime import datetime, timezone

from app.models.cubicaje import TIPO_REPORTE, CubicajeMensaje
from app.models.item import Item
from app.models.item_inspeccion import ItemInspeccionBodega
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.seguimiento import SeguimientoPedido
from app.models.user import RolUsuario


def _montar(db, crear_usuario, crear_cliente, crear_sesion, sufijo: str):
    vendedora = crear_usuario(f"ri{sufijo}v@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente(f"ri{sufijo}c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()

    pedido = PedidoGenerado(
        sesion_id=sesion.id,
        supplier="Prov",
        archivo_xlsx_url="https://x/pedido.xlsx",
        archivo_real_xlsx_url="https://x/real.xlsx",
        revisado_en_bodega_at=datetime.now(timezone.utc),
    )
    db.add(pedido)
    db.flush()
    db.add(PedidoGeneradoItem(
        pedido_generado_id=pedido.id, item_id=item.id, cantidad_pedida=3, cantidad_recibida=2,
    ))
    db.add(ItemInspeccionBodega(item_id=item.id, ctns=2, no_llego=True, fotos=["https://x/f.jpg"]))
    db.add(CubicajeMensaje(
        sesion_id=sesion.id, tipo=TIPO_REPORTE, mensaje="reporte", autor_id=vendedora.id, automatico=True,
    ))
    sesion.shipping_mark_bodega = "ZZZ"
    db.commit()
    return sesion, item, pedido


def test_reiniciar_deja_la_revision_como_al_principio(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    sesion, item, pedido = _montar(db, crear_usuario, crear_cliente, crear_sesion, "1")
    crear_usuario("ri1admin@test.com", rol=RolUsuario.admin)

    r = client.post(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion/reiniciar",
        headers={"Authorization": f"Bearer {token_staff('ri1admin@test.com')}"},
    )
    assert r.status_code == 200, r.text

    db.expire_all()
    assert db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id == item.id).count() == 0
    assert db.query(CubicajeMensaje).filter(
        CubicajeMensaje.sesion_id == sesion.id, CubicajeMensaje.tipo == TIPO_REPORTE
    ).count() == 0

    pg = db.query(PedidoGenerado).filter(PedidoGenerado.id == pedido.id).first()
    assert pg.revisado_en_bodega_at is None
    assert pg.archivo_real_xlsx_url is None
    # La orden que se le mandó al proveedor NO se toca: es lo que se vuelve a revisar.
    assert pg.archivo_xlsx_url == "https://x/pedido.xlsx"
    linea = db.query(PedidoGeneradoItem).filter(PedidoGeneradoItem.pedido_generado_id == pedido.id).first()
    assert linea.cantidad_pedida == 3
    assert linea.cantidad_recibida is None

    # La cotización del cliente queda intacta.
    assert db.query(Item).filter(Item.id == item.id).first() is not None


def test_bodega_puede_reiniciar_su_propia_revision(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    """Es su trabajo: si contó mal desde el primero, lo reinicia sin pedirle
    permiso a nadie."""
    from app.models.item_inspeccion import ItemInspeccionBodega

    sesion, item, _ = _montar(db, crear_usuario, crear_cliente, crear_sesion, "2")
    crear_usuario("ri2bod@test.com", rol=RolUsuario.bodega)

    r = client.post(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion/reiniciar",
        headers={"Authorization": f"Bearer {token_staff('ri2bod@test.com')}"},
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id == item.id).count() == 0


def test_la_vendedora_no_puede_reiniciar_la_revision(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    """Reiniciar es de quien revisa (bodega) o de Marcela, no de ventas."""
    sesion, _, _ = _montar(db, crear_usuario, crear_cliente, crear_sesion, "4")

    r = client.post(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion/reiniciar",
        headers={"Authorization": f"Bearer {token_staff('ri4v@test.com')}"},
    )
    assert r.status_code == 403, r.text


def test_no_se_reinicia_un_pedido_que_ya_salio_de_bodega(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    sesion, _, _ = _montar(db, crear_usuario, crear_cliente, crear_sesion, "3")
    crear_usuario("ri3admin@test.com", rol=RolUsuario.admin)
    db.add(SeguimientoPedido(sesion_id=sesion.id, estado="en_transito"))
    db.commit()

    r = client.post(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion/reiniciar",
        headers={"Authorization": f"Bearer {token_staff('ri3admin@test.com')}"},
    )
    assert r.status_code == 409, r.text
