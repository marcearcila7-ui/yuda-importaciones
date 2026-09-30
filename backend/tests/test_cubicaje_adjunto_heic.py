"""Un adjunto de cubicaje HEIC (foto de iPhone) se rechazaba de una con "Solo
se permiten fotos JPG, PNG, WEBP": este endpoint no sabía de HEIC, a
diferencia de reemplazar foto/inspección de bodega. Ahora lo acepta y lo
convierte a JPEG igual que el resto del sistema."""
import app.api.routes.cubicaje as rutas
from app.models.user import RolUsuario

# Cabecera mínima que detectar_tipo_imagen reconoce como HEIC (ver
# app/core/imagen_valida.py: bytes[4:8] == b"ftyp", bytes[8:12] en _MARCAS_HEIC).
HEIC_FALSO = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00" + b"\x00" * 20


def _storage_ok(monkeypatch):
    monkeypatch.setattr(rutas, "subir_foto", lambda contenido, nombre, tipo: "https://fake/foto.jpg")


def test_adjunto_heic_se_convierte_a_jpeg(db, client, crear_usuario, crear_sesion, token_staff, monkeypatch):
    vendedora = crear_usuario("cubheic1@test.com", rol=RolUsuario.vendedora)
    sesion = crear_sesion(vendedora.id)
    _storage_ok(monkeypatch)
    monkeypatch.setattr(rutas, "convertir_a_jpeg", lambda b: b"jpeg-bytes-convertidos")

    tok = token_staff("cubheic1@test.com")
    r = client.post(
        f"/api/v1/sesiones/{sesion.id}/cubicaje/adjunto",
        files={"archivo": ("foto.heic", HEIC_FALSO, "image/heic")},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["tipo"] == "imagen"


def test_adjunto_heic_que_no_se_puede_convertir_da_error_claro(
    db, client, crear_usuario, crear_sesion, token_staff, monkeypatch
):
    vendedora = crear_usuario("cubheic2@test.com", rol=RolUsuario.vendedora)
    sesion = crear_sesion(vendedora.id)
    _storage_ok(monkeypatch)
    monkeypatch.setattr(rutas, "convertir_a_jpeg", lambda b: None)

    tok = token_staff("cubheic2@test.com")
    r = client.post(
        f"/api/v1/sesiones/{sesion.id}/cubicaje/adjunto",
        files={"archivo": ("foto.heic", HEIC_FALSO, "image/heic")},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 400
    assert "iPhone" in r.json()["detail"]
