"""Si el pedido a la tienda se generó ANTES de que el cliente mandara sus
cantidades desde el portal, los archivos que quedaron para descargar llevan
las cajas viejas. La vendedora tiene que enterarse: si no, baja un Excel
equivocado y se lo manda al proveedor.
"""
from datetime import datetime, timezone

from app.models.item import Item
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.user import RolUsuario


def _pedido_con_lineas(db, sesion, cantidades: dict[str, int], vendedora_id: str):
    pedido = PedidoGenerado(
        sesion_id=sesion.id,
        supplier="Prov",
        archivo_xlsx_url="https://x/p.xlsx",
        generado_por_id=vendedora_id,
    )
    db.add(pedido)
    db.flush()
    for item_id, cajas in cantidades.items():
        db.add(PedidoGeneradoItem(pedido_generado_id=pedido.id, item_id=item_id, cantidad_pedida=cajas))
    db.commit()
    return pedido


def test_avisa_cuando_el_cliente_mando_otras_cantidades_despues_de_generar(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("pd1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientepd1@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()

    # Se generó el pedido con las cajas cotizadas (5).
    _pedido_con_lineas(db, sesion, {item.id: 5}, vendedora.id)
    h = {"Authorization": f"Bearer {token_staff('pd1@test.com')}"}

    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()[0]["cantidades_desactualizadas"] is False

    # Después el cliente mandó 2 cajas desde su portal: los archivos quedaron viejos.
    sesion.pedido_recibido_at = datetime.now(timezone.utc)
    item.cantidad_solicitada = 2
    db.commit()

    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers=h)
    assert r.json()[0]["cantidades_desactualizadas"] is True


def test_no_avisa_si_los_archivos_cuadran_con_lo_que_pidio_el_cliente(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("pd2@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientepd2@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()

    sesion.pedido_recibido_at = datetime.now(timezone.utc)
    item.cantidad_solicitada = 2
    db.commit()
    _pedido_con_lineas(db, sesion, {item.id: 2}, vendedora.id)

    h = {"Authorization": f"Bearer {token_staff('pd2@test.com')}"}
    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()[0]["cantidades_desactualizadas"] is False


def test_un_pedido_viejo_sin_lineas_no_se_marca_como_desactualizado(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    """Los pedidos de antes de que se guardaran las líneas no tienen con qué
    comparar: no se les inventa una alerta."""
    vendedora = crear_usuario("pd3@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientepd3@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    _pedido_con_lineas(db, sesion, {}, vendedora.id)

    h = {"Authorization": f"Bearer {token_staff('pd3@test.com')}"}
    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers=h)
    assert r.json()[0]["cantidades_desactualizadas"] is False
