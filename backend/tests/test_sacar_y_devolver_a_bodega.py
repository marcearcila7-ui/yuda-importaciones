"""Cuando bodega saca un pedido de su cola, el cliente tiene que dejar de ver
la inspección y volver a donde lo dejó la vendedora. Y Marcela puede
devolvérselo a bodega sin que el trabajo se anuncie dos veces.
"""
from app.models.seguimiento import SeguimientoPedido
from app.models.user import RolUsuario


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _seg(db, sesion_id):
    return db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).first()


def test_sacarlo_de_bodega_deshace_el_paso_y_le_quita_la_aprobacion_al_cliente(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    from datetime import datetime, timedelta, timezone

    vendedora = crear_usuario("sb1v@test.com", rol=RolUsuario.vendedora)
    crear_usuario("sb1b@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("sb1c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(SeguimientoPedido(
        sesion_id=sesion.id,
        estado="en_bodega",
        aprobacion_limite_at=datetime.now(timezone.utc) + timedelta(hours=48),
    ))
    db.commit()

    r = client.post(
        f"/api/v1/bodega/pedidos/{sesion.id}/archivar", headers=_h(token_staff("sb1b@test.com"))
    )
    assert r.status_code == 200, r.text

    db.expire_all()
    seg = _seg(db, sesion.id)
    # Vuelve a donde lo dejó la vendedora: el cliente ya no ve la inspección
    # ni tiene nada que aprobar.
    assert seg.estado == "proveedor_recibio"
    assert seg.aprobacion_limite_at is None
    assert seg.bodega_archivado_en is not None


def test_un_pedido_que_ya_viajo_no_se_puede_sacar_de_bodega(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("sb2v@test.com", rol=RolUsuario.vendedora)
    crear_usuario("sb2b@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("sb2c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(SeguimientoPedido(sesion_id=sesion.id, estado="en_transito"))
    db.commit()

    r = client.post(
        f"/api/v1/bodega/pedidos/{sesion.id}/archivar", headers=_h(token_staff("sb2b@test.com"))
    )
    assert r.status_code == 409, r.text
    db.expire_all()
    assert _seg(db, sesion.id).estado == "en_transito"


def test_marcela_lo_devuelve_a_bodega_y_no_se_puede_mandar_dos_veces(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    from datetime import datetime, timezone

    vendedora = crear_usuario("sb3v@test.com", rol=RolUsuario.vendedora)
    crear_usuario("sb3a@test.com", rol=RolUsuario.admin)
    cliente = crear_cliente("sb3c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(SeguimientoPedido(
        sesion_id=sesion.id, estado="proveedor_recibio",
        bodega_archivado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    h = _h(token_staff("sb3a@test.com"))
    r = client.post(f"/api/v1/bodega/pedidos/{sesion.id}/reenviar", headers=h)
    assert r.status_code == 200, r.text
    db.expire_all()
    assert _seg(db, sesion.id).bodega_archivado_en is None

    # Pulsarlo de nuevo no vuelve a anunciarle el trabajo a bodega.
    r = client.post(f"/api/v1/bodega/pedidos/{sesion.id}/reenviar", headers=h)
    assert r.status_code == 409, r.text


def test_la_vendedora_y_bodega_no_pueden_devolverlo(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    """Devolver un pedido a la cola es decisión de Marcela."""
    from datetime import datetime, timezone

    vendedora = crear_usuario("sb4v@test.com", rol=RolUsuario.vendedora)
    crear_usuario("sb4b@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("sb4c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(SeguimientoPedido(
        sesion_id=sesion.id, estado="proveedor_recibio",
        bodega_archivado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    for correo in ("sb4v@test.com", "sb4b@test.com"):
        r = client.post(f"/api/v1/bodega/pedidos/{sesion.id}/reenviar", headers=_h(token_staff(correo)))
        assert r.status_code == 403, (correo, r.text)
