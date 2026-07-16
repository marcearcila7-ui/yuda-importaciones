"""Validación de imágenes por 'magic bytes' (el contenido real del archivo), no
solo por el content-type declarado por el cliente, que es falsificable. Evita que
se suba y se sirva públicamente un archivo malicioso con un content-type mentido."""


def _es_jpeg(b: bytes) -> bool:
    return b[:3] == b"\xff\xd8\xff"


def _es_png(b: bytes) -> bool:
    return b[:8] == b"\x89PNG\r\n\x1a\n"


def _es_webp(b: bytes) -> bool:
    return len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"


# Orden de detección: content-type real -> función que reconoce su firma
_FIRMAS = {
    "image/jpeg": _es_jpeg,
    "image/png": _es_png,
    "image/webp": _es_webp,
}


def detectar_tipo_imagen(data: bytes) -> str | None:
    """Devuelve el content-type real según los primeros bytes del archivo, o None
    si el contenido no corresponde a un JPG/PNG/WEBP válido."""
    for tipo, coincide in _FIRMAS.items():
        if coincide(data):
            return tipo
    return None
