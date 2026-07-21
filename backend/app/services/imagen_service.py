import base64
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import httpx


def descargar_imagen_png(url: str, lado_px: int | None = None):
    """Descarga una imagen y la normaliza a PNG. Opcionalmente la achica a un
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
        pil.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception:
        return None


def descargar_imagenes_png(urls, lado_px: int | None = None, max_workers: int = 6) -> dict:
    """Descarga varias imágenes EN PARALELO y una sola vez por URL única.

    Devuelve {url: bytes_png} (omite las que fallan). Se usa para no bajar la
    misma foto dos veces (Excel + PDF) ni de forma secuencial.
    """
    unicas = [u for u in dict.fromkeys(urls) if u]
    if not unicas:
        return {}
    resultado: dict[str, bytes] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(unicas))) as ex:
        bufs = ex.map(lambda u: descargar_imagen_png(u, lado_px), unicas)
        for url, buf in zip(unicas, bufs):
            if buf is not None:
                resultado[url] = buf.getvalue()
    return resultado


def bytes_a_data_uri(png_bytes: bytes) -> str:
    """PNG en bytes → data URI base64 (para incrustar en HTML sin red)."""
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("ascii")
