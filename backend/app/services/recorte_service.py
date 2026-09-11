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

# Aire que se deja alrededor del recuadro final, en fraccion de su lado. Un
# recorte al ras se ve apretado; con el afinado por pixeles ya no hace falta tanto.
MARGEN = 0.025

# Hacia donde apunta el techo de las letras -> cuantos grados hay que girar la
# foto en sentido horario para enderezarla.
#
# Si el techo de las letras apunta a la DERECHA, la foto esta girada 90 grados en
# sentido horario respecto de lo normal, asi que se la devuelve girando 270.
GIRO_SEGUN_TEXTO = {"arriba": 0, "izquierda": 90, "abajo": 180, "derecha": 270}

# Cuanto se agranda el recuadro del modelo antes de buscar el borde real del
# producto. El modelo suele quedarse corto y cortar un pedazo, asi que se mira
# tambien un poco afuera de lo que marco.
BUSQUEDA = 0.10

# Que tan distinto de la mesa tiene que ser un pixel para contarlo como producto.
# Bajo de mas agarra la veta de la madera; alto de mas se come los bordes claros.
UMBRAL_FONDO = 34

# Lado al que se achica la region para buscar el borde. No hace falta full
# resolucion para saber donde termina un producto, y asi el analisis es instantaneo.
LADO_ANALISIS = 420

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


def _color_de_fondo(region):
    """Color de la mesa o el piso, estimado con el marco exterior de la region.

    Se mira el borde y no el centro a proposito: en el centro esta el producto.
    Se usa la mediana y no el promedio para que una esquina con sombra o un
    pedazo de cartel no arrastren el resultado.
    """
    ancho, alto = region.size
    grosor = max(2, min(ancho, alto) // 40)
    pixeles = []
    datos = region.load()
    for x in range(0, ancho, 2):
        for y in list(range(grosor)) + list(range(alto - grosor, alto)):
            pixeles.append(datos[x, y])
    for y in range(0, alto, 2):
        for x in list(range(grosor)) + list(range(ancho - grosor, ancho)):
            pixeles.append(datos[x, y])
    if not pixeles:
        return None
    canal = lambda i: sorted(p[i] for p in pixeles)[len(pixeles) // 2]  # noqa: E731
    return (canal(0), canal(1), canal(2))


def _borde_real(pil, caja_px):
    """Devuelve donde termina de verdad el producto dentro de `caja_px`, o None.

    El modelo marca de memoria y se pasa o se queda corto. Aca se mira la imagen:
    se estima el color de la mesa con el marco de la region, se marcan los pixeles
    que se apartan de ese color y se toma el rectangulo que los contiene. Funciona
    porque en estas fotos el producto esta apoyado sobre una superficie lisa.

    Nunca lanza: ante cualquier duda devuelve None y manda el recuadro del modelo.
    """
    try:
        from PIL import Image as PILImage
        from PIL import ImageChops, ImageFilter

        region = pil.crop(caja_px)
        if region.width < 40 or region.height < 40:
            return None
        escala = min(1.0, LADO_ANALISIS / max(region.size))
        chica = region.resize(
            (max(1, round(region.width * escala)), max(1, round(region.height * escala))),
            PILImage.BILINEAR,
        )

        fondo = _color_de_fondo(chica)
        if fondo is None:
            return None

        diferencia = ImageChops.difference(chica, PILImage.new("RGB", chica.size, fondo))
        gris = diferencia.convert("L")
        # La mediana borra la veta de la madera y el ruido sin comerse los bordes
        gris = gris.filter(ImageFilter.MedianFilter(5))
        mascara = gris.point(lambda v: 255 if v > UMBRAL_FONDO else 0)

        caja = mascara.getbbox()
        if caja is None:
            return None

        x0, y0, x1, y1 = (round(v / escala) for v in caja)
        area = (x1 - x0) * (y1 - y0)
        total = region.width * region.height
        # Si ocupa casi toda la region, el fondo no se pudo separar (mesa con
        # dibujo, foto a contraluz): no se afina nada. Si ocupa casi nada, el
        # umbral se comio el producto.
        if area > total * 0.97 or area < total * 0.05:
            return None

        return (caja_px[0] + x0, caja_px[1] + y0, caja_px[0] + x1, caja_px[1] + y1)
    except Exception:
        logger.exception("No se pudo afinar el recuadro")
        return None


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


def recortar_producto(
    imagen_bytes: bytes, recuadro: list[float] | None, giro: int = 0, afinar: bool = True
) -> bytes | None:
    """Recorta la foto al recuadro del producto. Devuelve JPEG o None si falla.

    `recuadro` es [x0, y0, x1, y1] en fracciones de 0 a 1; en None se usa la foto
    entera y solo se aplica el giro. `giro` son los grados en sentido horario
    para enderezarla (0, 90, 180 o 270): las fotos del mercado salen de costado
    porque se toman parandose al lado del producto.

    `afinar`: si el recuadro viene del MODELO (una adivinanza que puede
    quedarse corta o pasarse), conviene agrandarlo un poco y ajustarlo contra
    los pixeles reales (ver `_recortar`). Si el recuadro lo dibujo la vendedora
    A MANO, ya es exacto: afinarlo puede "corregir" una selección deliberada
    con la de otro objeto cercano en la foto, que es exactamente lo que NO se
    quiere cuando alguien ajusta el recorte a propósito.

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

        if recuadro is None:
            recorte = pil
        else:
            recorte = _recortar(pil, recuadro, afinar=afinar)
            if recorte is None:
                return None

        # El giro va DESPUES del recorte: el recuadro esta en las coordenadas de
        # la foto tal como la vio el modelo, o sea sin girar.
        if giro in (90, 180, 270):
            # PIL gira en sentido antihorario, y el modelo responde en horario
            recorte = recorte.rotate(-giro, expand=True)

        recorte.thumbnail((LADO_MAX, LADO_MAX))
        buf = BytesIO()
        recorte.save(buf, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
        return buf.getvalue()
    except Exception:
        logger.exception("No se pudo recortar la foto del producto")
        return None


def _recortar(pil, recuadro: list[float], afinar: bool = True):
    """Recorta al producto: el recuadro del modelo, afinado contra la imagen.

    Con `afinar=False` se respeta el recuadro tal cual, sin agrandarlo ni
    ajustarlo por color de fondo: es lo que hace falta cuando el recuadro lo
    dibujo una persona a mano, no el modelo."""
    try:
        ancho, alto = pil.size
        x0, y0, x1, y1 = recuadro

        if not afinar:
            caja = (
                int(x0 * ancho),
                int(y0 * alto),
                int(x1 * ancho),
                int(y1 * alto),
            )
            if caja[2] - caja[0] < 40 or caja[3] - caja[1] < 40:
                return None
            return pil.crop(caja)

        # 1. Se agranda lo que marco el modelo para mirar tambien un poco afuera:
        #    si se quedo corto, el borde real del producto esta ahi.
        bx = (x1 - x0) * BUSQUEDA
        by = (y1 - y0) * BUSQUEDA
        busqueda = (
            int(max(0.0, x0 - bx) * ancho),
            int(max(0.0, y0 - by) * alto),
            int(min(1.0, x1 + bx) * ancho),
            int(min(1.0, y1 + by) * alto),
        )

        # 2. Donde termina de verdad el producto, mirando los pixeles
        caja = _borde_real(pil, busqueda)
        if caja is None:
            # Sin afinado: se usa lo que marco el modelo, como antes
            caja = (
                int(x0 * ancho),
                int(y0 * alto),
                int(x1 * ancho),
                int(y1 * alto),
            )

        # 3. Un respiro alrededor para que no quede apretado
        ancho_caja = caja[2] - caja[0]
        alto_caja = caja[3] - caja[1]
        margen_x = round(ancho_caja * MARGEN)
        margen_y = round(alto_caja * MARGEN)
        caja = (
            max(0, caja[0] - margen_x),
            max(0, caja[1] - margen_y),
            min(ancho, caja[2] + margen_x),
            min(alto, caja[3] + margen_y),
        )

        if caja[2] - caja[0] < 40 or caja[3] - caja[1] < 40:
            # Recorte de menos de 40 px de lado: no sirve para ningun documento.
            return None
        return pil.crop(caja)
    except Exception:
        logger.exception("No se pudo aplicar el recuadro")
        return None
