"""Bodega marca en la inspección, producto por producto, si hay que devolverlo
al proveedor o si de plano no llegó. Al pasar de no marcado a marcado, debe
avisarse solo por el chat de cubicaje del pedido -sin repetir el aviso si
bodega vuelve a guardar con la casilla ya marcada de antes."""
from datetime import date

from app.models.cubicaje import TIPO_NOTA, CubicajeMensaje
from app.models.item import Item
from app.models.sesion import Sesion
from app.models.user import RolUsuario


def _crear_sesion_con_item(db, vendedora_id):
    sesion = Sesion(nombre_cliente="Cliente prueba", fecha=date.today(), user_id=vendedora_id)
    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    item = Item(
        sesion_id=sesion.id, supplier_nombre="Prov", item_no="RBOL1",
        descripcion_es="Bolso de prueba", ctns=5, qty_por_ctn=10, orden=1,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return sesion, item


def _payload_base(item_id, **overrides):
    base = {
        "item_id": item_id,
        "referencia": "RBOL1",
        "descripcion_es": "Bolso de prueba",
        "debe_devolver": False,
        "no_llego": False,
    }
    base.update(overrides)
    return base


def test_marcar_devolver_avisa_por_chat_una_sola_vez(db, client, crear_usuario, token_staff):
    crear_usuario("bodega-dev@test.com", rol=RolUsuario.bodega)
    vendedora = crear_usuario("v-dev@test.com", rol=RolUsuario.vendedora)
    sesion, item = _crear_sesion_con_item(db, vendedora.id)

    tok = token_staff("bodega-dev@test.com")
    headers = {"Authorization": f"Bearer {tok}"}

    r = client.put(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion",
        json={"items": [_payload_base(item.id, debe_devolver=True)]},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["debe_devolver"] is True

    mensajes = db.query(CubicajeMensaje).filter(CubicajeMensaje.sesion_id == sesion.id).all()
    assert len(mensajes) == 1
    assert mensajes[0].tipo == TIPO_NOTA
    assert "devolver" in mensajes[0].mensaje.lower()
    assert "RBOL1" in mensajes[0].mensaje

    # Guardar otra vez con la casilla YA marcada de antes: no debe duplicar el aviso.
    r2 = client.put(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion",
        json={"items": [_payload_base(item.id, debe_devolver=True)]},
        headers=headers,
    )
    assert r2.status_code == 200, r2.text
    mensajes_despues = db.query(CubicajeMensaje).filter(CubicajeMensaje.sesion_id == sesion.id).all()
    assert len(mensajes_despues) == 1


def test_marcar_no_llego_avisa_por_chat(db, client, crear_usuario, token_staff):
    crear_usuario("bodega-nl@test.com", rol=RolUsuario.bodega)
    vendedora = crear_usuario("v-nl@test.com", rol=RolUsuario.vendedora)
    sesion, item = _crear_sesion_con_item(db, vendedora.id)

    tok = token_staff("bodega-nl@test.com")
    r = client.put(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion",
        json={"items": [_payload_base(item.id, no_llego=True)]},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["items"][0]["no_llego"] is True

    mensajes = db.query(CubicajeMensaje).filter(CubicajeMensaje.sesion_id == sesion.id).all()
    assert len(mensajes) == 1
    assert "no lleg" in mensajes[0].mensaje.lower()
    assert "RBOL1" in mensajes[0].mensaje
