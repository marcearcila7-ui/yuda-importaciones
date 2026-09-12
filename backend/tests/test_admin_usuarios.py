"""Login insensible a mayúsculas/minúsculas y borrado de usuarios desde admin.

Cubre dos arreglos: el login de staff comparaba el email distinguiendo
mayúsculas (a diferencia del portal de clientes, que ya lo normalizaba), y
el panel de admin no tenía forma de borrar un usuario, solo desactivarlo.
"""
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


def test_no_puede_eliminarse_a_si_mismo(client, crear_usuario, token_staff):
    admin = crear_usuario("solito@yuda.com", rol=RolUsuario.admin)
    token = token_staff(admin.email)

    r = client.delete(
        f"/api/v1/admin/usuarios/{admin.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400, r.text
