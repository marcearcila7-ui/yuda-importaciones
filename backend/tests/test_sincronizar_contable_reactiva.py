"""Yuda Contable avisa a /clientes/sincronizar-desde-contable cada vez que crea
o edita un cliente allá. Si ese cliente ya existía acá pero estaba desactivado
(por ejemplo, se había borrado antes y ahora lo vuelven a crear con la misma
sigla), el aviso debe reactivarlo -no basta con actualizarle los datos de
contacto y dejarlo invisible para siempre."""
from app.core.config import settings
from app.models.user import RolUsuario


def test_sincronizar_reactiva_cliente_desactivado(
    monkeypatch, db, client, crear_usuario, crear_cliente
):
    monkeypatch.setattr(settings, "YUDA_CONTABLE_API_TOKEN", "token-de-prueba")
    crear_usuario("admin-sync@test.com", rol=RolUsuario.admin)
    vendedora = crear_usuario("v-sync@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("sv@test.com", vendedora.id, nombre="Sara Villegas", activo=False)
    cliente.sigla = "SV"
    db.commit()

    r = client.post(
        "/api/v1/clientes/sincronizar-desde-contable",
        json={"sigla": "sv", "nombre": "Sara Villegas", "telefono": "+573000000000"},
        headers={"Authorization": "Bearer token-de-prueba"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["activo"] is True

    db.refresh(cliente)
    assert cliente.activo is True
    assert cliente.telefono == "+573000000000"


def test_reactivar_archiva_cotizaciones_de_la_gestion_anterior(
    monkeypatch, db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    """Escenario real reportado: se borra un cliente, se vuelve a crear con la
    misma sigla y se reasigna a otra vendedora. Las cotizaciones de ANTES de
    borrarlo (con su propio chat de cubicaje) no deben aparecer mezcladas con
    el trabajo de la nueva vendedora."""
    monkeypatch.setattr(settings, "YUDA_CONTABLE_API_TOKEN", "token-de-prueba")
    crear_usuario("admin-arch@test.com", rol=RolUsuario.admin)
    vendedora_vieja = crear_usuario("vieja@test.com", rol=RolUsuario.vendedora)
    vendedora_nueva = crear_usuario("nueva@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("sv2@test.com", vendedora_vieja.id, nombre="Sara Villegas", activo=True)
    cliente.sigla = "SV2"
    db.commit()

    sesion_vieja = crear_sesion(vendedora_vieja.id, cliente.id, enviada=True)

    # Se borra el cliente (equivalente a lo que hace Yuda Contable al eliminarlo)
    cliente.activo = False
    db.commit()

    # Se vuelve a crear en Yuda Contable con la misma sigla y se reasigna
    r = client.post(
        "/api/v1/clientes/sincronizar-desde-contable",
        json={"sigla": "sv2", "nombre": "Sara Villegas"},
        headers={"Authorization": "Bearer token-de-prueba"},
    )
    assert r.status_code == 200, r.text
    cliente.vendedora_id = vendedora_nueva.id
    db.commit()

    db.refresh(sesion_vieja)
    assert sesion_vieja.archivada_en is not None

    sesion_nueva = crear_sesion(vendedora_nueva.id, cliente.id, enviada=True)

    token_nueva = token_staff("nueva@test.com")
    r = client.get("/api/v1/sesiones", headers={"Authorization": f"Bearer {token_nueva}"})
    assert r.status_code == 200, r.text
    ids_visibles = {s["id"] for s in r.json()}
    assert sesion_nueva.id in ids_visibles
    assert sesion_vieja.id not in ids_visibles

    r = client.get(
        f"/api/v1/clientes/{cliente.id}/cotizaciones",
        headers={"Authorization": f"Bearer {token_nueva}"},
    )
    assert r.status_code == 200, r.text
    ids_ficha = {s["id"] for s in r.json()}
    assert sesion_nueva.id in ids_ficha
    assert sesion_vieja.id not in ids_ficha


def test_sincronizar_sin_token_correcto_da_401(client, crear_usuario, crear_cliente):
    r = client.post(
        "/api/v1/clientes/sincronizar-desde-contable",
        json={"sigla": "SV", "nombre": "Sara Villegas"},
    )
    assert r.status_code in (401, 503), r.text
