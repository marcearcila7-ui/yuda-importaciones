"""El recorte automatico de la foto al producto.

Son pruebas puras: no tocan la API de vision ni el almacenamiento. Lo que se
verifica es que un recuadro malo nunca llegue a recortar (mejor la foto entera
que un producto cortado por la mitad) y que el recorte caiga donde debe.
"""

from io import BytesIO

from PIL import Image

from app.services.recorte_service import MARGEN, recortar_producto, recuadro_valido


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
