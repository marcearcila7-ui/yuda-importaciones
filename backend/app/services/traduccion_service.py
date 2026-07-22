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
_PISTAS_PROVEEDOR = ("公司", "工厂", "工艺厂", "商贸城", "市场", "有限", "号门")

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
