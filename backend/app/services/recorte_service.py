"""Recorte automatico de la foto del producto.

La vendedora saca UNA foto en el mercado: el producto junto al cartel con los
datos. Esa foto sirve para que el OCR lea el cartel, pero es fea para mandarsela
al cliente o al proveedor, que solo quieren ver el producto.

Antes existia una segunda foto "limpia" que habia que subir a mano, producto por
producto, despues de terminar la cotizacion. Nadie la usaba: era demasiado trabajo.
Ahora el mismo OCR devuelve el recuadro donde esta el producto y aca se recorta,
sin una sola llamada extra a la API de vision.
"""

import logging
from io import BytesIO

logger = logging.getLogger(__name__)

# Aire que se deja alrededor del recuadro que marco el modelo, en fraccion del
# lado del recorte. Un recorte al ras se ve apretado y ademas castiga cualquier
# imprecision del modelo cortando un pedazo del producto.
MARGEN = 0.04

# Calidad del JPEG del recorte. La misma que usa imagen_service para incrustar.
CALIDAD_JPEG = 88

# Lado maximo del recorte guardado. En los documentos se muestra a 300 px, y se
# guarda a 3x para que aguante impresion.
LADO_MAX = 900


def recuadro_valido(valor, area_maxima: float = 0.92) -> list[float] | None:
    """Normaliza el recuadro del producto o devuelve None.

    Descarta lo que no sirve para recortar: valores fuera de rango, esquinas al
    reves, y recuadros que cubren casi toda la foto (recortar ahi no aporta nada)
    o que son diminutos (seguro esta mal y cortaria el producto).
    """
    if not isinstance(valor, (list, tuple)) or len(valor) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(v) for v in valor)
    except (TypeError, ValueError):
        return None
    if not all(0.0 <= v <= 1.0 for v in (x0, y0, x1, y1)):
        return None
    if x1 <= x0 or y1 <= y0:
        return None
    area = (x1 - x0) * (y1 - y0)
    # Menos del 3% de la foto es casi seguro un error. El tope de arriba depende
    # de para que es el recuadro: recortar al 92% de la foto no aporta nada, pero
    # un cartel SI puede ocupar casi todo (y ahi el recorte sale de lo que queda).
    if area < 0.03 or area > area_maxima:
        return None
    return [x0, y0, x1, y1]


def recuadro_fuera_del_cartel(cartel: list[float]) -> list[float] | None:
    """Deduce donde esta el producto a partir de donde esta el cartel.

    Es el plan B cuando el modelo ubica el cartel que acaba de leer pero no se
    anima a marcar el producto. La idea es la de la propia vendedora: sacale el
    cartel a la foto y lo que queda es el producto. Se prueban las cuatro franjas
    que rodean al cartel (arriba, abajo, izquierda, derecha) y se toma la mas
    grande, que es donde tiene que estar.

    Devuelve None si ninguna franja es lo bastante grande como para contener algo.
    """
    x0, y0, x1, y1 = cartel
    franjas = [
        [0.0, 0.0, 1.0, y0],   # arriba del cartel
        [0.0, y1, 1.0, 1.0],   # abajo
        [0.0, 0.0, x0, 1.0],   # a la izquierda
        [x1, 0.0, 1.0, 1.0],   # a la derecha
    ]
    mejor = None
    mejor_area = 0.0
    for f in franjas:
        area = (f[2] - f[0]) * (f[3] - f[1])
        if area > mejor_area:
            mejor, mejor_area = f, area
    # Menos del 12% de la foto no alcanza para que ahi entre el producto entero
    if mejor is None or mejor_area < 0.12:
        return None
    return mejor


def recortar_producto(imagen_bytes: bytes, recuadro: list[float]) -> bytes | None:
    """Recorta la foto al recuadro del producto. Devuelve JPEG o None si falla.

    `recuadro` es [x0, y0, x1, y1] en fracciones de 0 a 1, ya validado por el OCR.
    Nunca lanza: si algo sale mal se devuelve None y se usa la foto completa,
    que es exactamente lo que pasaba antes de que existiera el recorte.
    """
    try:
        from PIL import Image as PILImage

        pil = PILImage.open(BytesIO(imagen_bytes))
        # EXIF: las fotos de celular vienen giradas y el recuadro que marco el
        # modelo esta en la orientacion que EL vio, o sea la ya enderezada.
        try:
            from PIL import ImageOps

            pil = ImageOps.exif_transpose(pil)
        except Exception:
            pass
        pil = pil.convert("RGB")

        ancho, alto = pil.size
        x0, y0, x1, y1 = recuadro

        # Aire alrededor, sin salirse de la foto
        margen_x = (x1 - x0) * MARGEN
        margen_y = (y1 - y0) * MARGEN
        x0 = max(0.0, x0 - margen_x)
        y0 = max(0.0, y0 - margen_y)
        x1 = min(1.0, x1 + margen_x)
        y1 = min(1.0, y1 + margen_y)

        caja = (
            int(x0 * ancho),
            int(y0 * alto),
            int(x1 * ancho),
            int(y1 * alto),
        )
        if caja[2] - caja[0] < 40 or caja[3] - caja[1] < 40:
            # Recorte de menos de 40 px de lado: no sirve para ningun documento.
            return None

        recorte = pil.crop(caja)
        recorte.thumbnail((LADO_MAX, LADO_MAX))
        buf = BytesIO()
        recorte.save(buf, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
        return buf.getvalue()
    except Exception:
        logger.exception("No se pudo recortar la foto del producto")
        return None
