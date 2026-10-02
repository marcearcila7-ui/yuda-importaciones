"""La vendedora corrige una cantidad en pantalla y genera el pedido: el
archivo tiene que salir con LO QUE ELLA ESCRIBIÓ, no con lo último que había
guardado. Antes, lo escrito solo se guardaba si además pulsaba "Enviar al
cliente para que confirme", que dice "(opcional)" y suena a otra cosa.
"""
from datetime import datetime, timezone

from app.models.item import Item
from app.models.sesion import Sesion
from app.models.user import RolUsuario


def test_guardar_cantidades_deja_escritas_las_cajas_sin_tocar_el_estado(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("gc1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientegc1@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()

    # El cliente pidió 2 cajas desde su portal.
    sesion.pedido_recibido_at = datetime.now(timezone.utc)
    sesion.pedido_estado = "recibido"
    item.cantidad_solicitada = 2
    db.commit()

    # La vendedora lo corrige a 7 en pantalla y genera.
    r = client.put(
        f"/api/v1/sesiones/{sesion.id}/cantidades",
        json={"items": [{"item_id": item.id, "cantidad": 7}]},
        headers={"Authorization": f"Bearer {token_staff('gc1@test.com')}"},
    )
    assert r.status_code == 200, r.text

    db.expire_all()
    assert db.query(Item).filter(Item.id == item.id).first().cantidad_solicitada == 7
    # Guardar no le pide nada al cliente: el estado se queda como estaba.
    assert db.query(Sesion).filter(Sesion.id == sesion.id).first().pedido_estado == "recibido"


def test_una_cantidad_en_cero_deja_el_producto_fuera_del_pedido(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("gc2@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientegc2@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()
    item.cantidad_solicitada = 4
    db.commit()

    r = client.put(
        f"/api/v1/sesiones/{sesion.id}/cantidades",
        json={"items": [{"item_id": item.id, "cantidad": 0}]},
        headers={"Authorization": f"Bearer {token_staff('gc2@test.com')}"},
    )
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.query(Item).filter(Item.id == item.id).first().cantidad_solicitada is None


def test_la_vendedora_de_otro_cliente_no_puede_tocar_las_cantidades(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    otra = crear_usuario("gc3@test.com", rol=RolUsuario.vendedora)
    crear_usuario("gc3b@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientegc3@test.com", otra.id)
    sesion = crear_sesion(otra.id, cliente.id, con_item=True)
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()

    r = client.put(
        f"/api/v1/sesiones/{sesion.id}/cantidades",
        json={"items": [{"item_id": item.id, "cantidad": 9}]},
        headers={"Authorization": f"Bearer {token_staff('gc3b@test.com')}"},
    )
    assert r.status_code == 403, r.text
