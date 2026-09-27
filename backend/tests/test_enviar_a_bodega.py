"""Regresión: enviar un pedido a bodega asignándolo de una vez a alguien no
debía fallar (bug real: actualizar_seguimiento pasó a devolver un objeto
Pydantic de solo lectura, y este endpoint intentaba mutarlo directo -sin
asignar a nadie nunca pasaba por ese código, por eso "enviar sin asignar" sí
funcionaba y "enviar asignando" no)."""
from app.models.pedido import PedidoGenerado
from app.models.user import RolUsuario


def test_enviar_a_bodega_asignando_a_alguien(db, client, crear_usuario, crear_cliente, crear_sesion, token_staff):
    vendedora = crear_usuario("vendedora@test.com", rol=RolUsuario.vendedora, nombre="Vendedora")
    bodega = crear_usuario("bodega@test.com", rol=RolUsuario.bodega, nombre="Bodega Uno")
    cliente = crear_cliente("cliente@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, enviada=True, con_item=True)

    db.add(PedidoGenerado(sesion_id=sesion.id, supplier="Prov_SN", archivo_xlsx_url="https://x/y.xlsx"))
    db.commit()

    token = token_staff("vendedora@test.com")
    r = client.post(
        f"/api/v1/pedidos/{sesion.id}/enviar-a-bodega",
        json={"asignado_a_id": bodega.id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["bodega_asignado_a_id"] == bodega.id
    assert data["estado"] == "proveedor_recibio"


def test_enviar_a_bodega_sin_asignar(db, client, crear_usuario, crear_cliente, crear_sesion, token_staff):
    vendedora = crear_usuario("vendedora2@test.com", rol=RolUsuario.vendedora, nombre="Vendedora Dos")
    cliente = crear_cliente("cliente2@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, enviada=True, con_item=True)

    db.add(PedidoGenerado(sesion_id=sesion.id, supplier="Prov_SN", archivo_xlsx_url="https://x/y.xlsx"))
    db.commit()

    token = token_staff("vendedora2@test.com")
    r = client.post(
        f"/api/v1/pedidos/{sesion.id}/enviar-a-bodega",
        json={"asignado_a_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["bodega_asignado_a_id"] is None
