"""Login insensible a mayúsculas/minúsculas y borrado de usuarios desde admin.

Cubre dos arreglos: el login de staff comparaba el email distinguiendo
mayúsculas (a diferencia del portal de clientes, que ya lo normalizaba), y
el panel de admin no tenía forma de borrar un usuario, solo desactivarlo.
"""
from datetime import date

from app.models.calendario import CalendarioTarea
from app.models.calendario_pagos import PagoTarea
from app.models.cubicaje import CubicajeVisto
from app.models.push_subscription import PushSubscription
from app.models.user import RolUsuario


def test_login_ignora_mayusculas_del_email(client, crear_usuario):
    crear_usuario("Nombre.Raro@Yuda.Com", rol=RolUsuario.vendedora)

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "nombre.raro@yuda.com", "password": "Clave1234!"},
    )
    assert r.status_code == 200, r.text


def test_login_ignora_mayusculas_aunque_se_escriban_al_reves(client, crear_usuario):
    crear_usuario("minuscula@yuda.com", rol=RolUsuario.vendedora)

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "MINUSCULA@YUDA.COM", "password": "Clave1234!"},
    )
    assert r.status_code == 200, r.text


def test_eliminar_usuario_sin_actividad(client, crear_usuario, token_staff):
    admin = crear_usuario("admin@yuda.com", rol=RolUsuario.admin)
    sin_actividad = crear_usuario("nueva@yuda.com", rol=RolUsuario.vendedora)
    token = token_staff(admin.email)

    r = client.delete(
        f"/api/v1/admin/usuarios/{sin_actividad.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204, r.text

    listado = client.get(
        "/api/v1/admin/usuarios", headers={"Authorization": f"Bearer {token}"}
    )
    ids = [u["id"] for u in listado.json()]
    assert sin_actividad.id not in ids


def test_no_elimina_usuario_con_cotizaciones(client, crear_usuario, crear_sesion, token_staff):
    admin = crear_usuario("admin2@yuda.com", rol=RolUsuario.admin)
    con_historial = crear_usuario("conhistorial@yuda.com", rol=RolUsuario.vendedora)
    crear_sesion(con_historial.id)
    token = token_staff(admin.email)

    r = client.delete(
        f"/api/v1/admin/usuarios/{con_historial.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 409, r.text

    listado = client.get(
        "/api/v1/admin/usuarios", headers={"Authorization": f"Bearer {token}"}
    )
    ids = [u["id"] for u in listado.json()]
    assert con_historial.id in ids


def test_eliminar_usuario_limpia_su_huella_en_push_calendario_y_pagos(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    """Reproduce el bug reportado: no se podía eliminar a un usuario real
    porque quedaban filas en push_subscriptions, cubicaje_vistos,
    calendario_tareas o pagos_tareas apuntándole -ninguna de ellas pasaba por
    el chequeo de "tiene cotizaciones/clientes", así que el borrado fallaba
    directo con un error de base de datos sin ni siquiera pedir confirmación."""
    admin = crear_usuario("admin3@yuda.com", rol=RolUsuario.admin, nombre="Marcela")
    objetivo = crear_usuario("conhuella@yuda.com", rol=RolUsuario.vendedora, nombre="Gilberto")

    # Sesión de OTRO usuario, solo para poder colgarle un cubicaje_visto al
    # usuario a eliminar sin disparar el conflicto de "tiene cotizaciones".
    sesion_ajena = crear_sesion(admin.id)
    cliente = crear_cliente("clientefondo@test.com", vendedora_id=admin.id, nombre="Cliente Fondo")

    db.add(PushSubscription(usuario_id=objetivo.id, endpoint="https://ejemplo.com/x", p256dh="a", auth="b"))
    db.add(CubicajeVisto(sesion_id=sesion_ajena.id, usuario_id=objetivo.id))
    tarea = CalendarioTarea(
        fecha=date(2026, 10, 5),
        tipo="recibe",
        marca_cliente="ABC",
        creado_por_id=objetivo.id,
        creado_por_nombre="Gilberto",
        actualizado_por_id=objetivo.id,
        actualizado_por_nombre="Gilberto",
    )
    db.add(tarea)
    pago = PagoTarea(
        fecha=date(2026, 10, 5),
        tienda="1234",
        cliente_id=cliente.id,
        cliente_sigla="CF",
        monto=100,
        estatus="no_pagado",
        creado_por_id=objetivo.id,
        creado_por_nombre="Gilberto",
    )
    db.add(pago)
    db.commit()

    token = token_staff(admin.email)
    r = client.delete(
        f"/api/v1/admin/usuarios/{objetivo.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 204, r.text

    # Las tareas/pagos no se borran (son tableros compartidos): sobreviven
    # con el id en null pero el nombre -guardado aparte- intacto.
    db.refresh(tarea)
    assert tarea.creado_por_id is None
    assert tarea.actualizado_por_id is None
    assert tarea.creado_por_nombre == "Gilberto"
    db.refresh(pago)
    assert pago.creado_por_id is None
    assert pago.creado_por_nombre == "Gilberto"


def test_no_puede_eliminarse_a_si_mismo(client, crear_usuario, token_staff):
    admin = crear_usuario("solito@yuda.com", rol=RolUsuario.admin)
    token = token_staff(admin.email)

    r = client.delete(
        f"/api/v1/admin/usuarios/{admin.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400, r.text
