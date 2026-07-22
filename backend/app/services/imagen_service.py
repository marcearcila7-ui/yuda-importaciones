import base64
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import httpx

# Las fotos de producto se incrustan como JPEG, no PNG: son fotografías, y en PNG
# cada una pesa ~550 KB (un pedido de 18 productos daba archivos de 10 MB, muy
# incómodos de mandar por WhatsApp). En JPEG de alta calidad pesan varias veces
# menos y a la vista son iguales.
CALIDAD_JPEG = 88


def descargar_imagen(url: str, lado_px: int | None = None):
    """Descarga una imagen y la normaliza a JPEG. Opcionalmente la achica a un
    cuadro de lado_px (mantiene proporción) para no inflar el archivo de salida.

    Devuelve un BytesIO listo para usar, o None si algo falla (nunca lanza).
    """
    try:
        # Timeout corto: si una foto tarda, se omite en vez de colgar la generación.
        resp = httpx.get(url, timeout=8, follow_redirects=True)
        if resp.status_code != 200:
            return None
        from PIL import Image as PILImage

        pil = PILImage.open(BytesIO(resp.content)).convert("RGB")
        if lado_px:
            pil.thumbnail((lado_px, lado_px))
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
        buf.seek(0)
        return buf
    except Exception:
        return None


def descargar_imagenes(urls, lado_px: int | None = None, max_workers: int = 6) -> dict:
    """Descarga varias imágenes EN PARALELO y una sola vez por URL única.

    Devuelve {url: bytes_jpeg} (omite las que fallan). Se usa para no bajar la
    misma foto dos veces (Excel + PDF) ni de forma secuencial.
    """
    unicas = [u for u in dict.fromkeys(urls) if u]
    if not unicas:
        return {}
    resultado: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(unicas))) as ex:
        bufs = ex.map(lambda u: descargar_imagen(u, lado_px), unicas)
        for url, buf in zip(unicas, bufs):
            if buf is not None:
                resultado[url] = buf.getvalue()
    return resultado


def bytes_a_data_uri(imagen_bytes: bytes) -> str:
    """JPEG en bytes → data URI base64 (para incrustar en HTML sin red)."""
    return "data:image/jpeg;base64," + base64.b64encode(imagen_bytes).decode("ascii")
