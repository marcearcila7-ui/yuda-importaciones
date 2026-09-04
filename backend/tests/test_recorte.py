"""El recorte automatico de la foto al producto.

Son pruebas puras: no tocan la API de vision ni el almacenamiento. Lo que se
verifica es que un recuadro malo nunca llegue a recortar (mejor la foto entera
que un producto cortado por la mitad) y que el recorte caiga donde debe.
"""

from io import BytesIO

from PIL import Image

from app.services.recorte_service import (
    MARGEN,
    recortar_producto,
    recuadro_fuera_del_cartel,
    recuadro_valido,
)


def _foto_de_prueba() -> bytes:
    """Foto sintetica de 1000x800: fondo blanco y el 'producto' rojo abajo a la derecha."""
    img = Image.new("RGB", (1000, 800), "white")
    for x in range(500, 1000):
        for y in range(400, 800):
            img.putpixel((x, y), (200, 30, 30))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


def test_recuadro_bueno_pasa():
    assert recuadro_valido([0.1, 0.2, 0.8, 0.9]) == [0.1, 0.2, 0.8, 0.9]


def test_recuadro_acepta_numeros_en_texto():
    # El modelo a veces devuelve los numeros como strings
    assert recuadro_valido(["0.1", "0.2", "0.8", "0.9"]) == [0.1, 0.2, 0.8, 0.9]


def test_recuadros_malos_se_descartan():
    malos = {
        "esquinas al reves": [0.9, 0.2, 0.1, 0.9],
        "fuera de rango": [-0.1, 0.2, 0.8, 0.9],
        "casi toda la foto": [0.0, 0.0, 1.0, 0.95],
        "diminuto": [0.5, 0.5, 0.51, 0.51],
        "texto": ["a", "b", "c", "d"],
        "faltan valores": [0.1, 0.2, 0.3],
        "vacio": None,
    }
    for motivo, valor in malos.items():
        assert recuadro_valido(valor) is None, motivo


def test_recorta_donde_esta_el_producto():
    recorte = recortar_producto(_foto_de_prueba(), [0.5, 0.5, 1.0, 1.0])
    assert recorte is not None

    img = Image.open(BytesIO(recorte))
    ancho, alto = img.size
    # 500x400 mas el margen de aire a cada lado
    assert ancho == round(500 * (1 + MARGEN))
    assert alto == round(400 * (1 + MARGEN))

    # El centro del recorte tiene que ser el producto, no el cartel blanco
    r, g, b = img.getpixel((ancho // 2, alto // 2))
    assert r > 150 and g < 80 and b < 80


def test_no_revienta_con_una_imagen_rota():
    # Ante cualquier problema se devuelve None y los documentos usan la foto entera
    assert recortar_producto(b"esto no es una imagen", [0.1, 0.1, 0.9, 0.9]) is None


def test_recuadro_del_cartel_puede_ser_casi_toda_la_foto():
    # Un cartel grande es valido: el recorte sale de lo que queda alrededor
    grande = [0.0, 0.0, 1.0, 0.96]
    assert recuadro_valido(grande) is None                      # como producto, no sirve
    assert recuadro_valido(grande, area_maxima=0.98) == grande   # como cartel, si


def test_deduce_el_producto_sacando_el_cartel():
    # Cartel abajo ocupando el 40% inferior: el producto tiene que estar arriba
    assert recuadro_fuera_del_cartel([0.0, 0.6, 1.0, 1.0]) == [0.0, 0.0, 1.0, 0.6]
    # Cartel a la izquierda: queda la franja derecha
    assert recuadro_fuera_del_cartel([0.0, 0.0, 0.35, 1.0]) == [0.35, 0.0, 1.0, 1.0]


def test_no_deduce_nada_si_el_cartel_tapa_casi_todo():
    # No queda espacio donde pueda estar el producto: mejor la foto entera
    assert recuadro_fuera_del_cartel([0.0, 0.0, 1.0, 0.95]) is None


def test_el_recorte_deducido_se_puede_aplicar():
    # El plan B tiene que producir un recuadro que el recortador acepte
    caja = recuadro_fuera_del_cartel([0.0, 0.55, 1.0, 1.0])
    assert caja is not None
    assert recortar_producto(_foto_de_prueba(), caja) is not None


def test_el_giro_es_en_sentido_horario():
    # Marca roja arriba a la izquierda. Al girar 90 en sentido horario tiene que
    # quedar arriba a la derecha, y los lados se intercambian.
    img = Image.new("RGB", (400, 800), "white")
    for x in range(80):
        for y in range(80):
            img.putpixel((x, y), (220, 20, 20))
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=95)
    original = buf.getvalue()

    def esquina_roja(datos: bytes) -> str:
        im = Image.open(BytesIO(datos))
        w, h = im.size
        puntos = {
            "sup-izq": (10, 10),
            "sup-der": (w - 10, 10),
            "inf-der": (w - 10, h - 10),
            "inf-izq": (10, h - 10),
        }
        for nombre, (x, y) in puntos.items():
            r, g, b = im.getpixel((x, y))
            if r > 150 and g < 90:
                return nombre
        return "ninguna"

    assert esquina_roja(recortar_producto(original, None, 0)) == "sup-izq"
    assert esquina_roja(recortar_producto(original, None, 90)) == "sup-der"
    assert esquina_roja(recortar_producto(original, None, 180)) == "inf-der"
    assert esquina_roja(recortar_producto(original, None, 270)) == "inf-izq"


def test_girar_sin_recuadro_no_recorta():
    # Girar la foto entera conserva la proporcion, solo intercambia los lados
    original = _foto_de_prueba()
    girada = recortar_producto(original, None, 90)
    assert girada is not None
    ancho, alto = Image.open(BytesIO(girada)).size
    # La de prueba es apaisada (1000x800); girada tiene que quedar vertical
    assert alto > ancho
