"""Reemplazar el archivo de una orden a proveedor: el navegador no siempre
manda el content-type "correcto" de un .xlsx (Excel/Numbers de Mac al
re-guardarlo a veces mandan "application/octet-stream" o "application/zip").
Antes eso se rechazaba con un 400 que la vendedora podía no notar -"como si
no hubiera cargado nada"- y el archivo nunca quedaba reemplazado."""
import app.api.routes.pedidos as rutas
from app.models.pedido import PedidoGenerado
from app.models.user import RolUsuario


def _storage_ok(monkeypatch):
    llamadas = {}

    def _fake(nombre_bucket):
        def _subir(contenido, nombre):
            llamadas["bucket"] = nombre_bucket
            llamadas["nombre"] = nombre
            return f"https://fake/{nombre_bucket}/{nombre}"

        return _subir

    monkeypatch.setattr(rutas, "subir_excel", _fake("pedidos"))
    monkeypatch.setattr(rutas, "subir_pdf", _fake("pedidos"))
    monkeypatch.setattr(rutas, "subir_csv", _fake("pedidos"))
    return llamadas


def _crear_pedido(db, crear_sesion, user_id):
    sesion = crear_sesion(user_id)
    pedido = PedidoGenerado(
        sesion_id=sesion.id,
        supplier="Prov_1",
        archivo_xlsx_url="https://fake/pedidos/original.xlsx",
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido


def _url(pedido_id):
    return f"/api/v1/pedidos/generados/{pedido_id}/reemplazar-archivo"


def test_reemplaza_xlsx_con_content_type_generico_de_mac(
    db, client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    llamadas = _storage_ok(monkeypatch)
    v = crear_usuario("v-reempl@test.com", RolUsuario.vendedora)
    pedido = _crear_pedido(db, crear_sesion, v.id)
    tok = token_staff("v-reempl@test.com")

    r = client.post(
        _url(pedido.id),
        headers={"Authorization": f"Bearer {tok}"},
        files={"archivo": ("Pedido corregido.xlsx", b"PK\x03\x04resto", "application/octet-stream")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["archivo_xlsx_url"] != "https://fake/pedidos/original.xlsx"
    assert llamadas["nombre"].endswith(".xlsx")

    db.refresh(pedido)
    assert pedido.archivo_xlsx_url == r.json()["archivo_xlsx_url"]


def test_reemplaza_pdf_con_extension_mayuscula(
    db, client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    _storage_ok(monkeypatch)
    v = crear_usuario("v-reempl2@test.com", RolUsuario.vendedora)
    pedido = _crear_pedido(db, crear_sesion, v.id)
    tok = token_staff("v-reempl2@test.com")

    r = client.post(
        _url(pedido.id),
        headers={"Authorization": f"Bearer {tok}"},
        files={"archivo": ("Pedido.PDF", b"%PDF-1.4 resto", "application/octet-stream")},
    )
    assert r.status_code == 200, r.text


def test_rechaza_archivo_que_no_es_ninguno_de_los_tres(
    db, client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    _storage_ok(monkeypatch)
    v = crear_usuario("v-reempl3@test.com", RolUsuario.vendedora)
    pedido = _crear_pedido(db, crear_sesion, v.id)
    tok = token_staff("v-reempl3@test.com")

    r = client.post(
        _url(pedido.id),
        headers={"Authorization": f"Bearer {tok}"},
        files={"archivo": ("nota.txt", b"esto no es un documento valido", "text/plain")},
    )
    assert r.status_code == 400, r.text
