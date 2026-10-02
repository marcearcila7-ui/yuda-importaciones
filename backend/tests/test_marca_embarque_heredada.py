"""La marca de embarque se hereda de la sigla del cliente en Yuda Contable:
la vendedora nunca la escribe a mano, ni al crear la cotización directo para
un cliente ni al vincular después una que empezó libre."""
from app.models.user import RolUsuario


def test_crear_sesion_hereda_marca_de_la_sigla(client, crear_usuario, crear_cliente, token_staff, db):
    from app.models.cliente import Cliente

    vendedora = crear_usuario("marca1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientemarca1@test.com", vendedora.id, nombre="Cliente Uno")
    cliente.sigla = "ABC"
    db.commit()

    token = token_staff("marca1@test.com")
    r = client.post(
        "/api/v1/sesiones",
        json={
            "nombre_cliente": "no importa, se pisa con el del cliente",
            "cliente_id": cliente.id,
            "tipo_cambio_usd": 6.7,
            "tipo_cotizacion": "productos",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["shipping_mark"] == "ABC"


def test_vincular_cliente_hereda_marca_de_la_sigla(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("marca2@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientemarca2@test.com", vendedora.id, nombre="Cliente Dos")
    cliente.sigla = "XYZ"
    db.commit()
    sesion = crear_sesion(vendedora.id, cliente_id=None, con_item=True)

    token = token_staff("marca2@test.com")
    r = client.patch(
        f"/api/v1/sesiones/{sesion.id}/cliente",
        json={"cliente_id": cliente.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["shipping_mark"] == "XYZ"


def test_marca_del_item_es_la_sigla_del_cliente(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    """La columna MARCA del packing list no se escribe a mano: sale de la
    sigla del cliente, aunque el ítem traiga otra cosa escrita de antes."""
    from app.models.item import Item

    vendedora = crear_usuario("marca3@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clientemarca3@test.com", vendedora.id, nombre="Cliente Tres")
    cliente.sigla = "KAES"
    db.commit()
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    sesion.shipping_mark = cliente.sigla
    db.query(Item).filter(Item.sesion_id == sesion.id).update({"marca": "escrita a mano"})
    db.commit()

    token = token_staff("marca3@test.com")
    r = client.get(f"/api/v1/sesiones/{sesion.id}/items", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert [i["marca"] for i in r.json()] == ["KAES"]
