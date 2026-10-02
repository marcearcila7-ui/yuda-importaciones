"""Bodega cuenta contra las cajas que de verdad se le PIDIERON a la tienda,
no contra las que se cotizaron. El caso real: la cotización decía 1 caja, el
cliente pidió 3, la orden que se le mandó al proveedor decía 3, y la pantalla
de revisión de bodega mostraba 1. La revisión se estaba haciendo contra el
número equivocado.
"""
from app.models.item import Item
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.user import RolUsuario
from app.services.inspeccion_service import construir_inspeccion_sesion


def _campo(resp, clave):
    return getattr(resp.items[0], clave)


def test_bodega_ve_las_cajas_de_la_orden_no_las_cotizadas(
    crear_usuario, crear_cliente, crear_sesion, db
):
    vendedora = crear_usuario("insp1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteinsp1@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    sesion.shipping_mark = "SV"
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()
    item.ctns = 1  # lo cotizado
    item.marca = None
    db.commit()

    pedido = PedidoGenerado(
        sesion_id=sesion.id, supplier="Prov", archivo_xlsx_url="https://x/p.xlsx"
    )
    db.add(pedido)
    db.flush()
    db.add(PedidoGeneradoItem(pedido_generado_id=pedido.id, item_id=item.id, cantidad_pedida=3))
    db.commit()

    resp = construir_inspeccion_sesion(db, sesion)
    assert _campo(resp, "cajas").original == 3, "bodega tiene que contar contra las 3 pedidas"
    # La marca sale de la sigla del cliente, no se escribe producto por producto.
    assert _campo(resp, "marca").original == "SV"


def test_sin_orden_generada_se_cae_a_las_cajas_cotizadas(
    crear_usuario, crear_cliente, crear_sesion, db
):
    """Cotizaciones que nunca generaron orden: no hay con qué comparar, se
    muestra lo cotizado en vez de dejar el campo vacío."""
    vendedora = crear_usuario("insp2@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteinsp2@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()
    item.ctns = 7
    db.commit()

    resp = construir_inspeccion_sesion(db, sesion)
    assert _campo(resp, "cajas").original == 7


def test_lo_que_corrigio_bodega_sigue_mandando(
    crear_usuario, crear_cliente, crear_sesion, db
):
    """Si bodega ya contó y corrigió, su número es el que vale como corregido:
    el de la orden sigue estando al lado como referencia de lo pedido."""
    from app.models.item_inspeccion import ItemInspeccionBodega

    vendedora = crear_usuario("insp3@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteinsp3@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()
    item.ctns = 1
    db.commit()

    pedido = PedidoGenerado(sesion_id=sesion.id, supplier="Prov", archivo_xlsx_url="https://x/p.xlsx")
    db.add(pedido)
    db.flush()
    db.add(PedidoGeneradoItem(pedido_generado_id=pedido.id, item_id=item.id, cantidad_pedida=3))
    db.add(ItemInspeccionBodega(item_id=item.id, ctns=2))  # solo llegaron 2
    db.commit()

    cajas = _campo(construir_inspeccion_sesion(db, sesion), "cajas")
    assert cajas.original == 3
    assert cajas.corregido == 2


def test_el_excel_de_correcciones_lleva_las_mismas_cajas_que_la_pantalla(
    crear_usuario, crear_cliente, crear_sesion, db
):
    """El Excel que bodega le devuelve a la vendedora y la pantalla de
    revisión tienen que decir lo mismo. Son dos caminos de código distintos y
    ya se desalinearon una vez."""
    from app.api.routes.bodega import _items_inspeccionados
    from app.models.item_inspeccion import ItemInspeccionBodega

    vendedora = crear_usuario("insp4@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteinsp4@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    sesion.shipping_mark = "SV"
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()
    item.ctns = 1   # lo cotizado
    item.marca = None
    db.commit()

    pedido = PedidoGenerado(sesion_id=sesion.id, supplier="Prov", archivo_xlsx_url="https://x/p.xlsx")
    db.add(pedido)
    db.flush()
    db.add(PedidoGeneradoItem(pedido_generado_id=pedido.id, item_id=item.id, cantidad_pedida=3))
    db.commit()

    # Bodega todavía no cuenta: manda lo que se le pidió a la tienda.
    fila = _items_inspeccionados(db, sesion.id)[0]
    assert fila.ctns == 3
    assert fila.marca == "SV"

    # Bodega cuenta 2: su número manda sobre todo lo demás.
    db.add(ItemInspeccionBodega(item_id=item.id, ctns=2))
    db.commit()
    assert _items_inspeccionados(db, sesion.id)[0].ctns == 2


def test_el_documento_original_ignora_lo_que_corrigio_bodega(
    crear_usuario, crear_cliente, crear_sesion, db
):
    """Es el punto de partida contra el que se contrasta: si trajera las
    correcciones de bodega, no habría contra qué comparar."""
    from app.api.routes.bodega import _items_inspeccionados, _items_originales
    from app.models.item_inspeccion import ItemInspeccionBodega

    vendedora = crear_usuario("orig1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteorig1@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    sesion.shipping_mark = "SV"
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()
    item.ctns = 1
    db.commit()

    pedido = PedidoGenerado(sesion_id=sesion.id, supplier="Prov", archivo_xlsx_url="https://x/p.xlsx")
    db.add(pedido)
    db.flush()
    db.add(PedidoGeneradoItem(pedido_generado_id=pedido.id, item_id=item.id, cantidad_pedida=3))
    db.add(ItemInspeccionBodega(item_id=item.id, ctns=2, descripcion_es="lo corrigió bodega"))
    db.commit()

    original = _items_originales(db, sesion.id)[0]
    corregido = _items_inspeccionados(db, sesion.id)[0]

    # El original dice lo que se pidió; el corregido, lo que bodega contó.
    assert original.ctns == 3
    assert corregido.ctns == 2
    assert original.descripcion_es != "lo corrigió bodega"
    assert corregido.descripcion_es == "lo corrigió bodega"
    assert original.marca == "SV"
