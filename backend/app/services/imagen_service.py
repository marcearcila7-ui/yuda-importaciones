from io import BytesIO

import httpx


def descargar_imagen_png(url: str, lado_px: int | None = None):
    """Descarga una imagen y la normaliza a PNG. Opcionalmente la achica a un
    cuadro de lado_px (mantiene proporción) para no inflar el archivo de salida.

    Devuelve un BytesIO listo para usar, o None si algo falla (nunca lanza).
    """
    try:
        resp = httpx.get(url, timeout=15)
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
