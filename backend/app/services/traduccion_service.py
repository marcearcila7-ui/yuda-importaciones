"""Traducción de descripciones de producto al chino (para el pedido al proveedor).

El OCR llena `descripcion_zh` con lo que alcanza a leer del cartel, que muchas
veces es el nombre o la dirección de la tienda, no el producto. Como el formato
de pedido debe llevar SIEMPRE la descripción en español y en chino, aquí se
traduce lo que falta y se guarda con el ítem (una sola vez por producto).
"""
import json
import logging

from anthropic import Anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

MODELO = "claude-opus-4-8"

# Señales de que el "chino" guardado es en realidad el letrero del proveedor
# (razón social, fábrica, puesto del mercado) y no el nombre del producto.
# Ojo: van los caracteres sueltos de "fábrica" en simplificado (厂) y tradicional
# (廠) porque los carteles usan las dos formas — con "工厂" solo no se detectaban
# casos reales como 义乌市瀚扬扇厂 o 龍創玻璃工艺制品廠.
_PISTAS_PROVEEDOR = (
    "公司", "厂", "廠", "商贸城", "商貿城", "市场", "市場",
    "有限", "号门", "批发", "批發",
)

_ESQUEMA = {
    "type": "object",
    "properties": {
        "traducciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "zh": {"type": "string"},
                },
                "required": ["id", "zh"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["traducciones"],
    "additionalProperties": False,
}

_cliente: Anthropic | None = None


def _get_cliente() -> Anthropic:
    global _cliente
    if _cliente is None:
        _cliente = Anthropic(api_key=settings.ANTHROPIC_API_KEY, max_retries=2)
    return _cliente


def descripcion_zh_util(item) -> bool:
    """¿El chino que tiene el ítem sirve como descripción del producto?"""
    zh = (getattr(item, "descripcion_zh", None) or "").strip()
    if not zh:
        return False
    if any(pista in zh for pista in _PISTAS_PROVEEDOR):
        return False
    # Si es idéntico al nombre del proveedor, tampoco describe el producto.
    proveedor = (getattr(item, "supplier_nombre", None) or "").strip()
    return not (proveedor and zh == proveedor)


def traducir_descripciones_zh(items: list) -> dict[str, str]:
    """Traduce al chino la descripción de los ítems dados. {item_id: texto_zh}.

    Va todo en UNA sola llamada (son descripciones cortas) y nunca lanza: si la
    traducción falla, el documento sale con la descripción en español, que es
    preferible a no poder generar el pedido.
    """
    pendientes = [
        (i.id, (i.descripcion_es or i.descripcion_en or "").strip())
        for i in items
    ]
    pendientes = [(id_, texto) for id_, texto in pendientes if texto]
    if not pendientes:
        return {}

    lista = "\n".join(f"{id_}\t{texto}" for id_, texto in pendientes)
    try:
        respuesta = _get_cliente().messages.create(
            model=MODELO,
            max_tokens=16000,
            system=(
                "Traduces descripciones de productos del mercado mayorista de Yiwu "
                "al chino simplificado, como las escribiría un comprador al hacer un "
                "pedido a su proveedor: nombre del producto con sus características "
                "clave, corto y natural. Sin explicaciones ni pinyin."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Traduce cada descripción al chino simplificado. Devuelve el "
                        "mismo id de cada línea.\n\n" + lista
                    ),
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": _ESQUEMA}},
        )
        texto = next(b.text for b in respuesta.content if b.type == "text")
        datos = json.loads(texto)
    except Exception:
        logger.exception("No se pudo traducir las descripciones al chino")
        return {}

    validos = {id_ for id_, _ in pendientes}
    return {
        t["id"]: t["zh"].strip()
        for t in datos.get("traducciones", [])
        if t.get("id") in validos and (t.get("zh") or "").strip()
    }


_ESQUEMA_COMPLETO = {
    "type": "object",
    "properties": {
        "descripciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "es": {"type": "string"},
                    "en": {"type": "string"},
                    "zh": {"type": "string"},
                    "uso": {"type": "string"},
                },
                "required": ["id", "es", "en", "zh", "uso"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["descripciones"],
    "additionalProperties": False,
}


def _falta_algo(item) -> bool:
    """¿A este producto le falta la descripción en algún idioma, o el uso?"""
    if not (getattr(item, "descripcion_es", None) or "").strip():
        return True
    if not (getattr(item, "descripcion_en", None) or "").strip():
        return True
    if not (getattr(item, "uso", None) or "").strip():
        return True
    return not descripcion_zh_util(item)


def completar_descripciones(db, items: list) -> int:
    """Deja los tres idiomas y el uso llenos en cada producto. Devuelve cuántos completó.

    La cotización del cliente lleva la descripción en español, inglés y chino,
    las tres. El OCR normalmente las trae, pero cuando la foto sale mal alguna
    queda vacía, y en el campo chino a veces deja el letrero de la tienda en
    lugar del producto. Dejar una celda en blanco en el documento que ve el
    cliente no es aceptable, asi que aquí se completan a partir de las que sí
    están y quedan guardadas: se traduce una vez por producto, no en cada
    exportación.

    Nunca lanza: si la traducción falla, el documento sale con lo que haya.
    """
    pendientes = [i for i in items if _falta_algo(i)]
    if not pendientes:
        return 0

    lineas = []
    for i in pendientes:
        base = " / ".join(
            t for t in (
                (i.descripcion_es or "").strip(),
                (i.descripcion_en or "").strip(),
                (i.material or "").strip(),
                (i.uso or "").strip(),
            ) if t
        )
        if base:
            lineas.append(f"{i.id}\t{base}")
    if not lineas:
        return 0

    try:
        respuesta = _get_cliente().messages.create(
            model=MODELO,
            max_tokens=16000,
            system=(
                "Escribes descripciones de productos del mercado mayorista de Yiwu "
                "para una cotización comercial, en español, inglés y chino "
                "simplificado, y dices para qué sirve. Describes SOLO lo que dice el "
                "texto que te dan: qué es el producto y sus características evidentes. "
                "Corto, claro y natural, como en un catálogo. El uso es la categoría "
                "en la que se usa, deducida del producto mismo y en dos o tres "
                "palabras: cocina, hogar, aseo personal, juguete, oficina, baño, "
                "decoración, mascotas, herramienta. Nunca inventes marcas, medidas ni "
                "materiales que no estén en el texto, y no agregues adjetivos de "
                "venta. Si el texto es pobre, la descripción es corta."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Para cada línea, devuelve la descripción del producto en los "
                        "tres idiomas y para qué sirve, con el mismo id.\n\n"
                        + "\n".join(lineas)
                    ),
                }
            ],
            output_config={"format": {"type": "json_schema", "schema": _ESQUEMA_COMPLETO}},
        )
        texto = next(b.text for b in respuesta.content if b.type == "text")
        datos = json.loads(texto)
    except Exception:
        logger.exception("No se pudieron completar las descripciones")
        return 0

    por_id = {i.id: i for i in pendientes}
    completados = 0
    for fila in datos.get("descripciones", []):
        item = por_id.get(fila.get("id"))
        if item is None:
            continue
        cambio = False
        for campo, clave in (("descripcion_es", "es"), ("descripcion_en", "en")):
            if not (getattr(item, campo) or "").strip() and (fila.get(clave) or "").strip():
                setattr(item, campo, fila[clave].strip())
                cambio = True
        if not descripcion_zh_util(item) and (fila.get("zh") or "").strip():
            item.descripcion_zh = fila["zh"].strip()
            cambio = True
        # El uso sale del producto, no del cartel: casi nunca esta escrito
        if not (item.uso or "").strip() and (fila.get("uso") or "").strip():
            item.uso = fila["uso"].strip()
            cambio = True
        if cambio:
            completados += 1

    if completados:
        db.commit()
    return completados
