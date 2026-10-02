"""El estado de cuenta de un cliente es información sensible: la vendedora no
lo ve, no lo descarga y nunca lo manda al portal. Eso lo gestiona Marcela
desde Yuda Contable.
"""
from app.models.user import RolUsuario


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_vendedora_no_recibe_el_estado_de_cuenta_en_la_lista_de_clientes(
    client, crear_usuario, crear_cliente, token_staff, db
):
    """Aunque no vea el botón, la URL del documento venía en la respuesta."""
    vendedora = crear_usuario("ec1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteec1@test.com", vendedora.id)
    cliente.estado_cuenta_oficial_url = "https://storage/pedidos/estado-cuenta-oficial/x.pdf"
    db.commit()

    r = client.get("/api/v1/clientes", headers=_headers(token_staff("ec1@test.com")))
    assert r.status_code == 200, r.text
    assert [c["estado_cuenta_oficial_url"] for c in r.json()] == [None]

    crear_usuario("ec1admin@test.com", rol=RolUsuario.admin)
    r = client.get("/api/v1/clientes", headers=_headers(token_staff("ec1admin@test.com")))
    assert r.status_code == 200, r.text
    urls = [c["estado_cuenta_oficial_url"] for c in r.json() if c["id"] == cliente.id]
    assert urls == ["https://storage/pedidos/estado-cuenta-oficial/x.pdf"]


def test_vendedora_no_puede_tocar_el_estado_de_cuenta_de_su_cliente(
    client, crear_usuario, crear_cliente, token_staff, db
):
    vendedora = crear_usuario("ec2@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteec2@test.com", vendedora.id)
    cliente.sigla = "ABC"
    db.commit()
    h = _headers(token_staff("ec2@test.com"))

    r = client.get(f"/api/v1/clientes/{cliente.id}/estado-cuenta-contable/pdf", headers=h)
    assert r.status_code == 403, r.text

    r = client.post(
        f"/api/v1/clientes/{cliente.id}/estado-cuenta-oficial",
        files={"archivo": ("cuenta.pdf", b"%PDF-1.4", "application/pdf")},
        headers=h,
    )
    assert r.status_code == 403, r.text

    r = client.delete(f"/api/v1/clientes/{cliente.id}/estado-cuenta-oficial", headers=h)
    assert r.status_code == 403, r.text
