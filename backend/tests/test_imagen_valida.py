from app.core.imagen_valida import detectar_tipo_imagen


def test_detecta_jpeg():
    assert detectar_tipo_imagen(b"\xff\xd8\xff\xe0" + b"\x00" * 20) == "image/jpeg"


def test_detecta_png():
    assert detectar_tipo_imagen(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20) == "image/png"


def test_detecta_webp():
    data = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 20
    assert detectar_tipo_imagen(data) == "image/webp"


def test_rechaza_no_imagen():
    # Un PDF con content-type de imagen mentido no debe pasar
    assert detectar_tipo_imagen(b"%PDF-1.4 contenido") is None
    assert detectar_tipo_imagen(b"") is None
    assert detectar_tipo_imagen(b"RIFF1234NOTW") is None
