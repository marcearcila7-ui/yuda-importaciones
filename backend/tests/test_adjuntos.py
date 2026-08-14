"""Adjuntos de una etapa del seguimiento: qué tipos de archivo se aceptan y qué
pasa cuando el storage no responde.

El tipo se decide por la extensión del nombre, no por el content-type: Windows
manda los .csv como "application/vnd.ms-excel" y varios navegadores mandan
"application/octet-stream".
"""
import app.api.routes.clientes as rutas
from app.models.user import RolUsuario


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


def _url(sesion_id):
    return f"/api/v1/sesiones/{sesion_id}/seguimiento/adjunto"


def _storage_ok(monkeypatch):
    """Evita salir a Supabase: guarda con qué se llamó y devuelve una URL falsa."""
    llamadas = {}

    def _doc(contenido, nombre, content_type):
        llamadas["bucket"] = "pedidos"
        llamadas["nombre"] = nombre
        llamadas["content_type"] = content_type
        return f"https://fake/pedidos/{nombre}"

    def _foto(contenido, nombre, content_type):
        llamadas["bucket"] = "fotos"
        llamadas["nombre"] = nombre
        llamadas["content_type"] = content_type
        return f"https://fake/fotos/{nombre}"

    monkeypatch.setattr(rutas, "subir_documento", _doc)
    monkeypatch.setattr(rutas, "subir_foto", _foto)
    return llamadas


def _subir(client, tok, sesion_id, nombre, contenido, content_type):
    return client.post(
        _url(sesion_id),
        headers=_h(tok),
        files={"archivo": (nombre, contenido, content_type)},
    )


def _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff):
    v = crear_usuario("v@y.com", RolUsuario.vendedora)
    s = crear_sesion(v.id, enviada=True)
    return s, token_staff("v@y.com")


def test_adjunta_csv(client, crear_usuario, crear_sesion, token_staff, monkeypatch):
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "medidas.csv", b"a,b\n1,2\n", "text/csv")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "csv"
    assert r.json()["nombre"] == "medidas.csv"
    assert llamadas["bucket"] == "pedidos"
    assert llamadas["nombre"].endswith(".csv")
    assert llamadas["content_type"] == "text/csv"


def test_adjunta_csv_con_content_type_de_windows(
    client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    # Windows manda los .csv como Excel; vale la extensión, no el content-type.
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "lista.csv", b"a,b\n", "application/vnd.ms-excel")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "csv"
    assert llamadas["content_type"] == "text/csv"


def test_adjunta_xlsx(client, crear_usuario, crear_sesion, token_staff, monkeypatch):
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "packing.xlsx", b"PK\x03\x04", "application/octet-stream")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "excel"
    assert llamadas["nombre"].endswith(".xlsx")
    assert "spreadsheetml" in llamadas["content_type"]


def test_adjunta_xls(client, crear_usuario, crear_sesion, token_staff, monkeypatch):
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "viejo.xls", b"\xd0\xcf", "application/vnd.ms-excel")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "excel"
    assert llamadas["content_type"] == "application/vnd.ms-excel"


def test_adjunta_pdf(client, crear_usuario, crear_sesion, token_staff, monkeypatch):
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "factura.pdf", b"%PDF-1.4", "application/pdf")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "pdf"
    assert llamadas["bucket"] == "pedidos"


def test_adjunta_imagen_va_al_bucket_de_fotos(
    client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "etiqueta.JPG", b"\xff\xd8\xff", "image/jpeg")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "imagen"
    assert llamadas["bucket"] == "fotos"
    assert llamadas["nombre"].endswith(".jpg")


def test_archivo_sin_extension_usa_el_content_type(
    client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    llamadas = _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "documento", b"%PDF-1.4", "application/pdf")
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "pdf"
    assert llamadas["nombre"].endswith(".pdf")


def test_rechaza_tipo_no_soportado(client, crear_usuario, crear_sesion, token_staff, monkeypatch):
    _storage_ok(monkeypatch)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "notas.txt", b"hola", "text/plain")
    assert r.status_code == 400
    assert "CSV" in r.json()["detail"]


def test_storage_caido_devuelve_502_con_mensaje(
    client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    def _falla(*_a, **_kw):
        raise RuntimeError("Name or service not known")

    monkeypatch.setattr(rutas, "subir_documento", _falla)
    s, tok = _sesion_de_vendedora(crear_usuario, crear_sesion, token_staff)
    r = _subir(client, tok, s.id, "medidas.csv", b"a,b\n", "text/csv")
    assert r.status_code == 502
    assert "almacenamiento" in r.json()["detail"]


def test_vendedora_ajena_no_puede_adjuntar(
    client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    _storage_ok(monkeypatch)
    v1 = crear_usuario("v1@y.com", RolUsuario.vendedora)
    crear_usuario("v2@y.com", RolUsuario.vendedora)
    s = crear_sesion(v1.id, enviada=True)
    tok2 = token_staff("v2@y.com")
    r = _subir(client, tok2, s.id, "medidas.csv", b"a,b\n", "text/csv")
    assert r.status_code in (403, 404)
