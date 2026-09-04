import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO

import httpx

# Las fotos de producto se incrustan como JPEG, no PNG: son fotografías, y en PNG
# cada una pesa ~550 KB (un pedido de 18 productos daba archivos de 10 MB, muy
# incómodos de mandar por WhatsApp). En JPEG de alta calidad pesan varias veces
# menos y a la vista son iguales.
CALIDAD_JPEG = 88

# Lado maximo al convertir una foto HEIC. Es el mismo tope que aplica el navegador
# a las demas fotos (comprimirImagen.ts) y el maximo que aprovecha Opus 5 leyendo.
# Sin esto, un HEIC de iPhone entra a 4284x5712 y pesa 3 MB, que en base64 son 4 MB:
# al borde del limite de 5 MB por imagen de la API, y sin ninguna ganancia de lectura.
LADO_MAX_HEIC = 2576

logger = logging.getLogger(__name__)


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


def convertir_a_jpeg(imagen_bytes: bytes) -> bytes | None:
    """Convierte una foto HEIC de iPhone a JPEG. Devuelve None si no se puede.

    Las fotos del iPhone salen en HEIC y nadie mas rio abajo las entiende: ni el
    navegador para mostrarlas, ni openpyxl para incrustarlas en el Excel, ni la
    API de vision. Se convierten una sola vez, al subirlas, y de ahi en adelante
    todo el sistema ve un JPEG normal.
    """
    try:
        from PIL import Image as PILImage

        # Registra el decodificador HEIC en Pillow (no viene de fabrica)
        try:
            from pillow_heif import register_heif_opener

            register_heif_opener()
        except Exception:
            logger.warning("pillow-heif no esta disponible: no se puede leer HEIC")
            return None

        pil = PILImage.open(BytesIO(imagen_bytes))
        try:
            from PIL import ImageOps

            pil = ImageOps.exif_transpose(pil)
        except Exception:
            pass
        pil = pil.convert("RGB")
        pil.thumbnail((LADO_MAX_HEIC, LADO_MAX_HEIC))
        buf = BytesIO()
        pil.save(buf, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
        return buf.getvalue()
    except Exception:
        logger.exception("No se pudo convertir la foto HEIC a JPEG")
        return None
