"""Tests de integración de los flujos críticos: login + rate-limit, aislamiento
del portal, permisos por dueño (IDOR) y el circuito de confirmación del pedido."""
from app.models.user import RolUsuario

LOGIN = "/api/v1/auth/login"


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


# ─────────── Login + rate-limit ───────────


def test_login_ok(client, crear_usuario):
    crear_usuario("v@y.com")
    r = client.post(LOGIN, json={"email": "v@y.com", "password": "Clave1234!"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_credenciales_malas(client, crear_usuario):
    crear_usuario("v@y.com")
    assert client.post(LOGIN, json={"email": "v@y.com", "password": "mala"}).status_code == 401


def test_login_usuario_inactivo(client, crear_usuario):
    crear_usuario("v@y.com", activo=False)
    assert client.post(LOGIN, json={"email": "v@y.com", "password": "Clave1234!"}).status_code == 403


def test_login_rate_limit(client, crear_usuario):
    crear_usuario("v@y.com")
    for _ in range(5):
        assert client.post(LOGIN, json={"email": "v@y.com", "password": "mala"}).status_code == 401
    # 6º intento: bloqueado
    assert client.post(LOGIN, json={"email": "v@y.com", "password": "mala"}).status_code == 429
    # Incluso con la clave correcta sigue bloqueado el email
    assert client.post(LOGIN, json={"email": "v@y.com", "password": "Clave1234!"}).status_code == 429


# ─────────── Aislamiento del portal ───────────


def test_portal_cliente_no_ve_cotizacion_ajena(
    client, crear_usuario, crear_cliente, crear_sesion, token_portal
):
    v = crear_usuario("v@y.com", RolUsuario.vendedora)
    crear_cliente("c1@y.com", v.id)
    c2 = crear_cliente("c2@y.com", v.id)
    s2 = crear_sesion(v.id, cliente_id=c2.id, enviada=True)
    tok1 = token_portal("c1@y.com")
    r = client.get(f"/api/v1/portal/cotizaciones/{s2.id}", headers=_h(tok1))
    assert r.status_code == 404


# ─────────── IDOR: permisos por dueño ───────────


def test_vendedora_no_accede_cotizacion_ajena(client, crear_usuario, crear_sesion, token_staff):
    v1 = crear_usuario("v1@y.com", RolUsuario.vendedora)
    v2 = crear_usuario("v2@y.com", RolUsuario.vendedora)
    s_v2 = crear_sesion(v2.id)
    h = _h(token_staff("v1@y.com"))
    # Ítems y generar-pedido de la cotización de v2 → 403
    assert client.get(f"/api/v1/sesiones/{s_v2.id}/items", headers=h).status_code == 403
    assert client.post(f"/api/v1/pedidos/{s_v2.id}/generar", headers=h).status_code == 403


def test_vendedora_si_accede_a_lo_suyo(client, crear_usuario, crear_sesion, token_staff):
    v1 = crear_usuario("v1@y.com", RolUsuario.vendedora)
    s_v1 = crear_sesion(v1.id)
    h = _h(token_staff("v1@y.com"))
    assert client.get(f"/api/v1/sesiones/{s_v1.id}/items", headers=h).status_code == 200


def test_lotes_ocr_por_dueno(client, crear_usuario, crear_sesion, token_staff):
    v1 = crear_usuario("v1@y.com", RolUsuario.vendedora)
    v2 = crear_usuario("v2@y.com", RolUsuario.vendedora)
    s_v2 = crear_sesion(v2.id)
    h1 = _h(token_staff("v1@y.com"))
    h2 = _h(token_staff("v2@y.com"))
    # v1 no puede crear lote ni ver el lote activo de la cotización de v2
    assert client.post(f"/api/v1/sesiones/{s_v2.id}/lotes", headers=h1).status_code == 403
    assert client.get(f"/api/v1/sesiones/{s_v2.id}/lotes/activo", headers=h1).status_code == 403
    # v2 crea el lote en lo suyo
    r = client.post(f"/api/v1/sesiones/{s_v2.id}/lotes", headers=h2)
    assert r.status_code == 201
    lote_id = r.json()["lote_id"]
    # v1 no puede consultar, procesar ni borrar ese lote ajeno
    assert client.get(f"/api/v1/lotes/{lote_id}", headers=h1).status_code == 403
    assert client.post(f"/api/v1/lotes/{lote_id}/procesar", headers=h1).status_code == 403
    assert client.delete(f"/api/v1/lotes/{lote_id}", headers=h1).status_code == 403


def test_admin_ve_cotizacion_de_cualquiera(client, crear_usuario, crear_sesion, token_staff):
    crear_usuario("a@y.com", RolUsuario.admin)
    v = crear_usuario("v@y.com", RolUsuario.vendedora)
    s_v = crear_sesion(v.id)
    h = _h(token_staff("a@y.com"))
    assert client.get(f"/api/v1/sesiones/{s_v.id}/items", headers=h).status_code == 200


# ─────────── Circuito de confirmación del pedido ───────────


def test_generar_requiere_confirmacion(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, token_portal
):
    v = crear_usuario("v@y.com", RolUsuario.vendedora)
    c = crear_cliente("c@y.com", v.id)
    s = crear_sesion(v.id, cliente_id=c.id, enviada=True)
    hc = _h(token_portal("c@y.com"))
    hv = _h(token_staff("v@y.com"))

    item_id = client.get(f"/api/v1/portal/cotizaciones/{s.id}", headers=hc).json()["items"][0]["item_id"]

    # 1) El cliente propone cantidades → estado recibido
    r = client.put(
        f"/api/v1/portal/cotizaciones/{s.id}/pedido",
        headers=hc,
        json={"items": [{"item_id": item_id, "cantidad": 3}], "notas": "surtidos"},
    )
    assert r.status_code == 200

    # 2) Generar pedido con cantidades del cliente ANTES de confirmar → 400
    r = client.post(f"/api/v1/pedidos/{s.id}/generar?usar_cantidades_cliente=true", headers=hv)
    assert r.status_code == 400

    # 3) La vendedora ajusta a 5 y envía a confirmar → por_confirmar
    r = client.put(
        f"/api/v1/sesiones/{s.id}/enviar-a-confirmar",
        headers=hv,
        json={"items": [{"item_id": item_id, "cantidad": 5}]},
    )
    assert r.status_code == 200
    assert r.json()["pedido_estado"] == "por_confirmar"

    # 4) El cliente confirma → confirmado, con las 5 cajas de la vendedora
    r = client.post(f"/api/v1/portal/cotizaciones/{s.id}/confirmar", headers=hc)
    assert r.status_code == 200
    d = client.get(f"/api/v1/portal/cotizaciones/{s.id}", headers=hc).json()
    assert d["pedido_estado"] == "confirmado"
    assert d["items"][0]["cantidad_solicitada"] == 5


def test_confirmar_sin_estar_por_confirmar_falla(
    client, crear_usuario, crear_cliente, crear_sesion, token_portal
):
    v = crear_usuario("v@y.com", RolUsuario.vendedora)
    c = crear_cliente("c@y.com", v.id)
    s = crear_sesion(v.id, cliente_id=c.id, enviada=True)
    hc = _h(token_portal("c@y.com"))
    # Sin pedido enviado, no se puede confirmar
    assert client.post(f"/api/v1/portal/cotizaciones/{s.id}/confirmar", headers=hc).status_code == 409


# ─────────── Paginación del historial ───────────


def test_historial_paginacion(client, crear_usuario, crear_sesion, token_staff):
    crear_usuario("a@y.com", RolUsuario.admin)
    v = crear_usuario("v@y.com", RolUsuario.vendedora)
    for _ in range(3):
        crear_sesion(v.id)
    h = _h(token_staff("a@y.com"))
    base = "/api/v1/historial/sesiones"

    # Sin limit: comportamiento anterior, devuelve todo (3)
    assert len(client.get(base, headers=h).json()) == 3
    # Primera página de 2
    assert len(client.get(f"{base}?limit=2&offset=0", headers=h).json()) == 2
    # Segunda página: queda 1
    assert len(client.get(f"{base}?limit=2&offset=2", headers=h).json()) == 1
