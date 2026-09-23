"""Validación de documentos por 'magic bytes' (el contenido real del
archivo), mismo espíritu que imagen_valida.py pero para PDF/Excel: el
content-type y la extensión que manda el cliente son falsificables."""


def _es_pdf(b: bytes) -> bool:
    return b[:5] == b"%PDF-"


def _es_xlsx(b: bytes) -> bool:
    # .xlsx es en realidad un .zip (Office Open XML)
    return b[:4] == b"PK\x03\x04"


def _es_xls(b: bytes) -> bool:
    # Formato binario viejo de Excel: contenedor OLE2/CFB
    return b[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


_FIRMAS_DOCUMENTO = {
    "application/pdf": _es_pdf,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": _es_xlsx,
    "application/vnd.ms-excel": _es_xls,
}


def detectar_tipo_documento(data: bytes) -> str | None:
    """Devuelve el content-type real (PDF o Excel) según los primeros bytes,
    o None si el contenido no corresponde a ninguno de los dos."""
    for tipo, coincide in _FIRMAS_DOCUMENTO.items():
        if coincide(data):
            return tipo
    return None


def _es_video_familia_mp4(b: bytes) -> bool:
    # MP4/MOV/M4V son contenedores ISO-BMFF: la mayoría trae la caja "ftyp" en
    # el byte 4. QuickTime viejo a veces arranca directo con otro átomo
    # conocido sin ftyp -se acepta también para no rechazar videos legítimos.
    if len(b) < 8:
        return False
    return b[4:8] in (b"ftyp", b"moov", b"mdat", b"free", b"wide", b"skip")


def _es_webm(b: bytes) -> bool:
    return b[:4] == b"\x1a\x45\xdf\xa3"  # EBML/Matroska


def es_video_valido(data: bytes) -> bool:
    """True si el contenido real corresponde a un MP4/MOV o WEBM válido."""
    return _es_video_familia_mp4(data) or _es_webm(data)
