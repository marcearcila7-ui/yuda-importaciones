"""El numerito de la pestaña "Cubicaje": cuántos mensajes del otro lado no ha
visto todavía quien está mirando. Se pone en cero al abrir el chat (que es lo
que marca "visto").
"""
from datetime import datetime, timedelta, timezone

from app.models.cubicaje import TIPO_NOTA, CubicajeMensaje, CubicajeVisto
from app.models.user import RolUsuario


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _contar(client, sesion_id, token):
    r = client.get(f"/api/v1/sesiones/{sesion_id}/cubicaje/no-leidos", headers=_h(token))
    assert r.status_code == 200, r.text
    return r.json()["no_leidos"]


def test_cuenta_los_del_otro_lado_y_no_los_propios(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("cnl1v@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("cnl1b@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("cnl1c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)

    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo=TIPO_NOTA, autor_id=bodega.id, mensaje="no llegó"))
    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo=TIPO_NOTA, autor_id=bodega.id, mensaje="y este tampoco"))
    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo=TIPO_NOTA, autor_id=vendedora.id, mensaje="ok, gracias"))
    db.commit()

    # La vendedora tiene 2 por leer (los de bodega); lo suyo no cuenta.
    assert _contar(client, sesion.id, token_staff("cnl1v@test.com")) == 2
    # Bodega tiene 1 por leer (el de la vendedora).
    assert _contar(client, sesion.id, token_staff("cnl1b@test.com")) == 1


def test_abrir_el_chat_lo_deja_en_cero(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("cnl2v@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("cnl2b@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("cnl2c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo=TIPO_NOTA, autor_id=bodega.id, mensaje="hola"))
    db.commit()

    token = token_staff("cnl2v@test.com")
    assert _contar(client, sesion.id, token) == 1

    # Esto es lo que manda el chat mientras está abierto y en foco.
    r = client.post(f"/api/v1/sesiones/{sesion.id}/cubicaje/visto", headers=_h(token))
    assert r.status_code == 204, r.text
    assert _contar(client, sesion.id, token) == 0


def test_un_mensaje_nuevo_despues_de_haberlo_visto_vuelve_a_contar(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("cnl3v@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("cnl3b@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("cnl3c@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)

    hace_rato = datetime.now(timezone.utc) - timedelta(hours=1)
    db.add(CubicajeVisto(sesion_id=sesion.id, usuario_id=vendedora.id, visto_en=hace_rato))
    db.add(CubicajeMensaje(
        sesion_id=sesion.id, tipo=TIPO_NOTA, autor_id=bodega.id, mensaje="viejo",
        created_at=hace_rato - timedelta(minutes=5),
    ))
    db.commit()
    token = token_staff("cnl3v@test.com")
    assert _contar(client, sesion.id, token) == 0

    db.add(CubicajeMensaje(
        sesion_id=sesion.id, tipo=TIPO_NOTA, autor_id=bodega.id, mensaje="nuevo",
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    assert _contar(client, sesion.id, token) == 1
