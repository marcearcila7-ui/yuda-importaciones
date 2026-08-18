"""Conversión de números del OCR y cobertura de idiomas del prompt.

Los carteles del mercado de Yiwu vienen en español, inglés o chino. El prompt pide
dígitos arábigos, pero un cartel manuscrito en chino puede devolver el número en
ancho completo o en numerales chinos, así que la conversión los entiende igual.
"""
import pytest

from app.services.ocr_service import PROMPT, _a_numero, _numero_chino


@pytest.mark.parametrize(
    "valor,esperado",
    [
        (12.5, 12.5),
        ("17", 17.0),
        ("¥12.8", 12.8),
        ("1,200", 1200.0),
        ("单价 8.5", 8.5),
        ("１２０", 120.0),          # dígitos de ancho completo (teclado chino)
        ("１２．５", 12.5),
        ("十二", 12.0),            # numerales chinos
        ("二十五", 25.0),
        ("一百二十", 120.0),
        ("三百", 300.0),
        ("两", 2.0),
        ("三点五", 3.5),
        ("一手10个", 10.0),        # gana el dígito arábigo si lo hay
        (None, None),
        (True, None),
        ("sin numero", None),
        ("", None),
    ],
)
def test_a_numero(valor, esperado):
    assert _a_numero(valor) == esperado


@pytest.mark.parametrize(
    "valor,esperado",
    [("十二", 12), ("二十五", 25), ("１４４", 144), ("240", 240)],
)
def test_a_numero_entero(valor, esperado):
    resultado = _a_numero(valor, entero=True)
    assert resultado == esperado
    assert isinstance(resultado, int)


def test_numero_chino_rechaza_texto_no_numerico():
    assert _numero_chino("塑料杯") is None
    assert _numero_chino("") is None


# El prompt es el que hace que el OCR lea inglés y chino; si alguien recorta estas
# variantes, el OCR vuelve a leer solo español y nadie se entera hasta producción.
@pytest.mark.parametrize(
    "etiqueta",
    [
        "单价",      # precio
        "每箱",      # piezas por caja
        "起订量",    # cantidad mínima
        "体积",      # CBM
        "毛重",      # peso bruto
        "摊位",      # tienda / stand
        "UNIT PRICE",
        "QTY/CTN",
        "MIN ORDER",
        "GROSS WEIGHT",
    ],
)
def test_prompt_cubre_ingles_y_chino(etiqueta):
    assert etiqueta in PROMPT


def test_prompt_fija_el_idioma_de_salida():
    # Aunque el cartel esté en chino, las descripciones salen en los tres idiomas.
    assert "El idioma del cartel NO cambia el idioma de la respuesta" in PROMPT
