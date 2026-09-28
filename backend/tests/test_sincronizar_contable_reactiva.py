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


def test_sincronizar_sin_token_correcto_da_401(client, crear_usuario, crear_cliente):
    r = client.post(
        "/api/v1/clientes/sincronizar-desde-contable",
        json={"sigla": "SV", "nombre": "Sara Villegas"},
    )
    assert r.status_code in (401, 503), r.text
