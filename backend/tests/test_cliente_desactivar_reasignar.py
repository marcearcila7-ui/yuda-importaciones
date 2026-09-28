"""Solo Marcela puede hacer desaparecer un cliente del sistema (lo desactiva,
no lo borra), y solo ella puede reasignarlo a otra vendedora. Al reasignar o
desactivar, la vendedora anterior pierde el acceso por completo -incluso a
lo que ella misma haya creado para ese cliente."""
from app.models.pedido import PedidoGenerado
from app.models.seguimiento import SeguimientoPedido
from app.models.user import RolUsuario


def test_vendedora_no_puede_eliminar_cliente(client, crear_usuario, crear_cliente, token_staff):
    vendedora = crear_usuario("v1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("c1@test.com", vendedora.id)
    token = token_staff("v1@test.com")

    r = client.delete(f"/api/v1/clientes/{cliente.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403, r.text


def test_admin_eliminar_cliente_desactiva_sin_borrar_nada(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    admin = crear_usuario("admin1@test.com", rol=RolUsuario.admin)
    vendedora = crear_usuario("v2@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("c2@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)

    token = token_staff("admin1@test.com")
    r = client.delete(f"/api/v1/clientes/{cliente.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 204, r.text

    db.refresh(cliente)
    assert cliente.activo is False
    # Nada se borró: la cotización y sus datos siguen existiendo, como respaldo.
    from app.models.sesion import Sesion

    assert db.query(Sesion).filter(Sesion.id == sesion.id).first() is not None


def test_vendedora_no_puede_desactivar_cliente_por_patch(client, crear_usuario, crear_cliente, token_staff):
    vendedora = crear_usuario("v3@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("c3@test.com", vendedora.id)
    token = token_staff("v3@test.com")

    r = client.patch(
        f"/api/v1/clientes/{cliente.id}",
        json={"activo": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403, r.text


def test_vendedora_pierde_acceso_a_cotizacion_al_reasignar_cliente(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    admin = crear_usuario("admin2@test.com", rol=RolUsuario.admin)
    vendedora_a = crear_usuario("va@test.com", rol=RolUsuario.vendedora)
    vendedora_b = crear_usuario("vb@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("c4@test.com", vendedora_a.id)
    # La cotización la creó la vendedora A para su propio cliente.
    sesion = crear_sesion(vendedora_a.id, cliente.id, con_item=True)

    token_a = token_staff("va@test.com")
    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200, r.text

    # Marcela reasigna el cliente a la vendedora B.
    token_admin = token_staff("admin2@test.com")
    r = client.patch(
        f"/api/v1/clientes/{cliente.id}",
        json={"vendedora_id": vendedora_b.id},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r.status_code == 200, r.text

    # La vendedora A ya no puede ver esa cotización, aunque ella la haya creado.
    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 403, r.text

    # La vendedora B, dueña nueva, sí puede.
    token_b = token_staff("vb@test.com")
    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 200, r.text


def test_vendedora_pierde_acceso_a_cotizacion_si_cliente_se_desactiva(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    admin = crear_usuario("admin3@test.com", rol=RolUsuario.admin)
    vendedora = crear_usuario("v5@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("c5@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)

    token = token_staff("v5@test.com")
    token_admin = token_staff("admin3@test.com")
    client.delete(f"/api/v1/clientes/{cliente.id}", headers={"Authorization": f"Bearer {token_admin}"})

    r = client.get(f"/api/v1/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403, r.text


def test_vendedora_no_puede_borrar_cotizacion_de_cliente(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    vendedora = crear_usuario("v6@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("c6@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    token = token_staff("v6@test.com")

    r = client.delete(f"/api/v1/sesiones/{sesion.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403, r.text


def test_vendedora_si_puede_borrar_cotizacion_libre(client, crear_usuario, crear_sesion, token_staff):
    vendedora = crear_usuario("v7@test.com", rol=RolUsuario.vendedora)
    sesion = crear_sesion(vendedora.id, cliente_id=None, con_item=True)
    token = token_staff("v7@test.com")

    r = client.delete(f"/api/v1/sesiones/{sesion.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text


def test_listar_clientes_oculta_inactivos_para_vendedora(client, crear_usuario, crear_cliente, token_staff):
    vendedora = crear_usuario("v8@test.com", rol=RolUsuario.vendedora)
    crear_cliente("activo@test.com", vendedora.id, nombre="Activo", activo=True)
    crear_cliente("inactivo@test.com", vendedora.id, nombre="Inactivo", activo=False)
    token = token_staff("v8@test.com")

    r = client.get("/api/v1/clientes", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    nombres = [c["nombre"] for c in r.json()]
    assert nombres == ["Activo"]


def test_bodega_no_ve_pedidos_de_cliente_inactivo(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    vendedora = crear_usuario("v9@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("bodega9@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("c9@test.com", vendedora.id, activo=False)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(SeguimientoPedido(sesion_id=sesion.id, estado="proveedor_recibio"))
    db.add(PedidoGenerado(sesion_id=sesion.id, supplier="Prov_SN", archivo_xlsx_url="https://x/y.xlsx"))
    db.commit()

    token = token_staff("bodega9@test.com")
    r = client.get("/api/v1/bodega/pedidos?vista=sin_asignar", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert sesion.id not in [p["sesion_id"] for p in r.json()]


def test_bodega_pierde_acceso_al_detalle_si_cliente_se_desactiva(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    """Bodega puede trabajar el pedido de cualquier vendedora, pero si Marcela
    desactiva al cliente mientras bodega tiene el detalle abierto, debe
    perder el acceso igual que la vendedora -no seguir viendo ni actualizando
    un pedido de un cliente que ya no existe en el sistema."""
    admin = crear_usuario("admin10@test.com", rol=RolUsuario.admin)
    vendedora = crear_usuario("v10@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("bodega10@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("c10@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(SeguimientoPedido(sesion_id=sesion.id, estado="proveedor_recibio"))
    db.commit()

    token_bodega = token_staff("bodega10@test.com")
    r = client.get(f"/api/v1/bodega/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token_bodega}"})
    assert r.status_code == 200, r.text
    r = client.get(f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion", headers={"Authorization": f"Bearer {token_bodega}"})
    assert r.status_code == 200, r.text

    token_admin = token_staff("admin10@test.com")
    r = client.delete(f"/api/v1/clientes/{cliente.id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert r.status_code == 204, r.text

    r = client.get(f"/api/v1/bodega/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token_bodega}"})
    assert r.status_code == 403, r.text
    r = client.get(f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion", headers={"Authorization": f"Bearer {token_bodega}"})
    assert r.status_code == 403, r.text

    # Admin sigue viendo todo, cliente inactivo o no.
    r = client.get(f"/api/v1/bodega/pedidos/{sesion.id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert r.status_code == 200, r.text
