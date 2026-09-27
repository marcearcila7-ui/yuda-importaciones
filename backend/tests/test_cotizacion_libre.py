"""Una cotización libre (sin cliente asociado) es solo consultiva: no debe
poder generar pedido a proveedor ni enviarse a bodega."""
from app.models.pedido import PedidoGenerado
from app.models.user import RolUsuario


def test_generar_pedidos_bloqueado_sin_cliente(db, client, crear_usuario, crear_sesion, token_staff):
    vendedora = crear_usuario("libre1@test.com", rol=RolUsuario.vendedora, nombre="Vendedora Libre")
    sesion = crear_sesion(vendedora.id, cliente_id=None, con_item=True)

    token = token_staff("libre1@test.com")
    r = client.post(
        f"/api/v1/pedidos/{sesion.id}/generar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400, r.text
    assert "libre" in r.json()["detail"].lower()


def test_enviar_a_bodega_bloqueado_sin_cliente(db, client, crear_usuario, crear_sesion, token_staff):
    vendedora = crear_usuario("libre2@test.com", rol=RolUsuario.vendedora, nombre="Vendedora Libre Dos")
    sesion = crear_sesion(vendedora.id, cliente_id=None, con_item=True)

    # Aunque de algún modo existiera un PedidoGenerado, el envío a bodega debe
    # seguir bloqueado sin cliente asociado.
    db.add(PedidoGenerado(sesion_id=sesion.id, supplier="Prov_SN", archivo_xlsx_url="https://x/y.xlsx"))
    db.commit()

    token = token_staff("libre2@test.com")
    r = client.post(
        f"/api/v1/pedidos/{sesion.id}/enviar-a-bodega",
        json={"asignado_a_id": None},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400, r.text
    assert "libre" in r.json()["detail"].lower()
