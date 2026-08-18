import base64
import json
import logging
import re

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.core.ocr_limiter import slot_ocr

logger = logging.getLogger(__name__)

# Modelo de visión a utilizar
MODELO = "claude-opus-4-5-20251101"

# Cliente único reutilizado (evita abrir una conexión nueva por cada foto).
# max_retries: el SDK reintenta con backoff exponencial ante 429 / 5xx / errores de red.
_client: AsyncAnthropic | None = None

def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=settings.OCR_MAX_RETRIES,
        )
    return _client

# Prompt fijo enviado a Claude Vision (no configurable desde la UI)
PROMPT = """
Eres un experto en productos del mercado mayorista de Yiwu, China.
En la imagen hay UN PRODUCTO y, normalmente, un cartel/tablero blanco, una tarjeta, o datos escritos A MANO directamente sobre el piso o la mesa.

Tu tarea tiene DOS partes y debes combinarlas:
1. IDENTIFICA visualmente qué producto es mirando la foto (qué es, de qué material parece, para qué sirve).
2. LEE el cartel/tablero/etiqueta/tarjeta y extrae los datos escritos (precio, proveedor, medidas, etc.).

Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, sin bloques de código, sin comillas adicionales.

El JSON debe tener exactamente estas claves:
{
  "descripcion_es": "qué es el producto, en español, claro y específico (ej: 'Vaso plástico con tapa y sorbete') o null",
  "descripcion_en": "lo mismo en inglés (ej: 'Plastic cup with lid and straw') o null",
  "descripcion_zh": "la MISMA descripción del producto traducida al chino simplificado (ej: '带盖带吸管的塑料杯'). NUNCA copies aquí el nombre de la tienda, la razón social ni la dirección del cartel: solo el producto",
  "material": "material principal que ves (plástico, metal, vidrio, cerámica, tela, madera, silicona, papel...) o null",
  "uso": "categoría o uso del producto (cocina, hogar, juguete, oficina, baño, decoración, mascotas...) o null",
  "supplier_nombre": "nombre o CÓDIGO de la tienda/proveedor (string o null)",
  "supplier_numero": "número de stand o booth, o teléfono de la tarjeta (string o null)",
  "price_rmb": número decimal del PRECIO unitario en yuan/RMB o null,
  "qty_por_ctn": número entero de piezas por caja o null,
  "largo_cm": null (SIEMPRE null),
  "ancho_cm": null (SIEMPRE null),
  "alto_cm": null (SIEMPRE null),
  "cbm_directo": número decimal del CBM (cubicaje/volumen por caja) o null,
  "gw": número decimal del peso bruto por caja en kg o null,
  "colores": "colores o variantes disponibles como string separado por comas o null",
  "cantidad_minima": número entero de la mínima cantidad de compra o null,
  "notas": "cualquier otra información relevante o null",
  "confianza": "alta, media o baja según tu certeza en la extracción",
  "legible": true o false (booleano),
  "motivo_ilegible": "si legible es false, el problema en una o dos palabras (ej: 'borrosa', 'oscura', 'recortada'); si legible es true, null"
}

IDIOMA DEL CARTEL — el cartel/tarjeta puede estar escrito en ESPAÑOL, en INGLÉS, en CHINO o mezclando los tres (es normal que el precio esté en chino y el resto en español). DEBES leer los tres idiomas por igual: un rótulo en chino o en inglés vale exactamente lo mismo que uno en español y hay que extraer su dato. El chino puede venir manuscrito, en simplificado o en tradicional, y a veces escrito en vertical. Los números pueden estar en dígitos normales, en dígitos de ancho completo (１２３) o en caracteres chinos (十二 = 12, 两 = 2, 二十五 = 25): conviértelos SIEMPRE a dígitos arábigos normales. "点" entre dos números es la coma decimal (三点五 = 3.5).

El idioma del cartel NO cambia el idioma de la respuesta: descripcion_es va SIEMPRE en español, descripcion_en SIEMPRE en inglés y descripcion_zh SIEMPRE en chino simplificado, aunque el cartel esté escrito en chino o en inglés.

MUY IMPORTANTE — los datos vienen escritos a mano, con letra irregular, abreviaturas y a veces errores de ortografía. El texto PUEDE ESTAR ROTADO (de costado 90°, o 180°) porque la foto se tomó girada: LÉELO igual, gira mentalmente la imagen si hace falta. Los tableros blancos suelen tener REFLEJOS/BRILLOS de la luz: esfuérzate en leer a través del brillo. Reconoce SIEMPRE estos datos, con TODAS sus variantes en los TRES idiomas:

• PRECIO unitario (yuan/RMB) → price_rmb. Aparece como:
  - español: "PRECIO", "PRECIO:", "P:"
  - inglés: "PRICE", "UNIT PRICE", "U/P", "U.P."
  - chino: "价格", "單價" / "单价", "售价", "批发价", "零售价"
  - un número precedido por el símbolo YUAN "¥" o "￥" o "元" o "RMB" o una "Y" suelta, o seguido de "元" o "块" (ej: "¥22" → 22 ; "¥ 12.8" → 12.8 ; "PRECIO: 17" → 17 ; "单价 8.5" → 8.5 ; "12元" → 12 ; "8块5" → 8.5)
  Cualquiera de esas formas ES el precio unitario.

• PIEZAS/UNIDADES por CAJA (cartón) → qty_por_ctn. Aparece como cualquiera de estos rótulos, con o sin dos puntos, y el número puede ir ANTES o DESPUÉS:
  - español: "CX", "CAJA X", "CAJAX", "CJ X", "C/X", "X/CAJA", "PCS", "PC", "PZ", "PZS", "PIEZAS", "UNID", "U/CAJA"
  - inglés: "PCS/CTN", "QTY/CTN", "PCS PER CARTON", "CTN QTY", "PACKING", "P/C", "PER CARTON"
  - chino: "每箱", "一箱", "箱装", "装箱量", "装箱数", "入数", y las formas con unidad + 箱: "件/箱", "个/箱", "只/箱", "支/箱", "双/箱", "套/箱"
  Ejemplos: "CX: 200" → 200 ; "CAJA X: 120" → 120 ; "200 PCS" → 200 ; "pcs 30" → 30 ; "每箱 240" → 240 ; "一箱100个" → 100 ; "QTY/CTN: 144" → 144

• CBM (cubicaje/volumen por caja) → cbm_directo. Variantes:
  - "CBM", "CMB" (letras invertidas, es lo mismo), con o sin dos puntos
  - inglés: "MEAS", "MEASUREMENT", "VOLUME", "M3", "M³"
  - chino: "体积", "體積", "材积", "立方", "立方米", "外箱体积"
  Ejemplos: "CBM: 0.22" → 0.22 ; "cbm 0.11" → 0.11 ; "体积 0.08" → 0.08

• CANTIDAD MÍNIMA de compra → cantidad_minima. Variantes:
  - español/inglés con ortografía manuscrita: "MOQ", "MQT", "MOA", "MOG", "MQO", "MINIMO", "MIN", "MIN ORDER", "MIN. QTY", "MINIMUM"
  - chino: "起订量", "起訂量", "最少", "最低", "最低起订", "起批", "最少订购", y "一手" (en Yiwu "una mano" es la unidad mínima de compra: si dice "一手10个" la mínima es 10)
  Extrae SOLO el número aunque diga "10 cajas" o "5 x tienda" (ej: "MOQ: 600" → 600 ; "moa 10" → 10 ; "moq: 5 x tienda" → 5 ; "起订量 20" → 20)

• PESO BRUTO por caja (kg) → gw. Variantes: "PESO", "PESO BRUTO"; inglés "G.W.", "GW", "GROSS WEIGHT", "KGS", "KG"; chino "毛重", "重量", "公斤", "千克" (ej: "G.W. 12.5" → 12.5 ; "毛重 9公斤" → 9)

• TIENDA / PROVEEDOR → supplier_nombre. Variantes:
  - español/inglés: "TIENDA", "TIENDA:", "BOOTH", "BOOTH NO.", "STAND", "SHOP", "STALL"
  - chino: "摊位", "攤位", "商位", "展位", "店铺", "铺号", "档口"
  - o directamente un CÓDIGO de stand tipo "F1-10968", "G3-17951", "Fr-2406"
  Va SIEMPRE en supplier_nombre (aunque sea un código), NUNCA en supplier_numero. Si en el tablero NO hay TIENDA pero hay una TARJETA DE VISITA del proveedor, usa el nombre de la tarjeta (ej: "CHIBAO" / "驰豹") para supplier_nombre y el teléfono para supplier_numero (en las tarjetas chinas el teléfono viene rotulado "电话", "手机" o "TEL").

• Puede haber otros rótulos: "DESCRIPCION" (texto libre del producto; en inglés "DESCRIPTION" / "ITEM", en chino "品名", "名称", "产品"), "TAMAÑO"/medidas (ej "20x10x9"; en inglés "SIZE", en chino "尺寸", "规格"), "LOGO", colores/variantes (ej "PLATA/TIRA/CADENA"; en inglés "COLOR", en chino "颜色", "色"). Usa la descripción y los colores si ayudan, pero NO pongas las medidas en largo/ancho/alto.

Reglas:
- SIEMPRE identifica el producto y completa descripcion_es y descripcion_en mirando la foto, aunque el cartel no traiga descripción. Debe ser específica del producto que ves, no genérica.
- material y uso: infiérelos de la imagen aunque no estén escritos; si no podés deducirlo, null.
- Si un dato NUMÉRICO no aparece, usa null; nunca inventes números. Pero si en el tablero SÍ está el precio, las piezas por caja, el CBM o la cantidad mínima (en cualquiera de sus variantes de arriba), DEBES extraerlos: no los dejes en null.
- largo_cm, ancho_cm y alto_cm van SIEMPRE en null: son las medidas de la CAJA FINAL, que se cargan a mano después. Aunque el cartel muestre medidas (ej "28x23x12"), NO las pongas ahí.
- price_rmb, qty_por_ctn, cbm_directo, gw, cantidad_minima deben ser números (float o int) o null, nunca strings.
- confianza es obligatorio, nunca null.
- Que el cartel esté escrito en chino o en inglés NO es motivo para marcar legible=false ni para bajar la confianza: los tres idiomas son igual de válidos y sus datos deben extraerse igual.
- legible es obligatorio, nunca null: evalúa SOLO si se puede LEER el texto. Un reflejo/brillo o que la foto esté rotada NO la hacen ilegible por sí solos. Marca legible=false SOLO si el texto realmente no se distingue (muy borroso, movido, muy oscuro, tapado o cortado). Ante la duda por buena calidad, marca true.
"""


def _resultado_vacio() -> dict:
    """Devuelve un resultado con todos los campos en null y confianza baja"""
    return {
        "descripcion_es": None,
        "descripcion_en": None,
        "descripcion_zh": None,
        "material": None,
        "uso": None,
        "supplier_nombre": None,
        "supplier_numero": None,
        "price_rmb": None,
        "qty_por_ctn": None,
        "largo_cm": None,
        "ancho_cm": None,
        "alto_cm": None,
        "cbm_directo": None,
        "gw": None,
        "colores": None,
        "cantidad_minima": None,
        "notas": None,
        "confianza": "baja",
        # Si no se pudo procesar la foto, se considera no legible: la vendedora
        # deberá volver a tomarla.
        "legible": False,
        "motivo_ilegible": "no_procesada",
    }


def _parsear_json(texto: str) -> dict | None:
    """Intenta parsear el JSON de la respuesta; busca el bloque { ... } si falla"""
    try:
        return json.loads(texto)
    except Exception:
        pass
    try:
        inicio = texto.index("{")
        fin = texto.rindex("}")
        return json.loads(texto[inicio : fin + 1])
    except Exception:
        return None


# Dígitos de ancho completo (teclados chinos) -> dígitos normales
_ANCHO_COMPLETO = str.maketrans("０１２３４５６７８９．", "0123456789.")

# Numerales chinos, para los carteles escritos a mano en chino. El prompt pide
# dígitos arábigos, pero si igual vuelve "十二" conviene entenderlo que perderlo.
_DIGITOS_ZH = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
               "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_UNIDADES_ZH = {"十": 10, "百": 100, "千": 1000}


def _numero_chino(texto: str) -> float | None:
    """Convierte un numeral chino simple (hasta millares) a número, o None.

    Cubre lo que aparece en un cartel: 十二 = 12, 二十五 = 25, 三百 = 300,
    一百二十 = 120, y el decimal con 点 (三点五 = 3.5).
    """
    texto = texto.strip()
    if not texto or any(c not in _DIGITOS_ZH and c not in _UNIDADES_ZH and c != "点" for c in texto):
        return None

    if "点" in texto:
        entera, _, decimal = texto.partition("点")
        base = _numero_chino(entera) if entera else 0
        if base is None or not decimal:
            return None
        digitos = "".join(str(_DIGITOS_ZH[c]) for c in decimal if c in _DIGITOS_ZH)
        if len(digitos) != len(decimal):
            return None
        return float(f"{int(base)}.{digitos}")

    total = 0
    actual = 0
    for caracter in texto:
        if caracter in _DIGITOS_ZH:
            actual = _DIGITOS_ZH[caracter]
        else:
            unidad = _UNIDADES_ZH[caracter]
            # "十二" = 12: el 十 sin dígito delante vale 1 decena
            total += (actual or 1) * unidad
            actual = 0
    return float(total + actual)


def _a_numero(valor, entero: bool = False):
    """Convierte un valor a número (o None). Extrae el número si viene como string"""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return int(valor) if entero else float(valor)
    if isinstance(valor, str):
        texto = valor.translate(_ANCHO_COMPLETO).replace(",", "")
        coincidencia = re.search(r"-?\d+(?:\.\d+)?", texto)
        if coincidencia:
            numero = float(coincidencia.group())
        else:
            numero = _numero_chino(texto)
            if numero is None:
                return None
        return int(numero) if entero else numero
    return None


async def extraer_datos_etiqueta(imagen_bytes: bytes, media_type: str) -> dict:
    """Extrae datos de una etiqueta de proveedor usando Claude Vision.

    Nunca lanza excepciones: ante cualquier fallo devuelve un resultado vacío
    con confianza baja.
    """
    # 1. Imagen a base64
    base64_string = base64.standard_b64encode(imagen_bytes).decode("utf-8")

    # 2-4. Llamada a la API de Anthropic (cliente único + tope global de concurrencia
    # respaldado por Postgres, válido aun con varias réplicas).
    try:
        client = _get_client()
        async with slot_ocr():
            response = await client.messages.create(
                model=MODELO,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_string,
                                },
                            },
                            {
                                "type": "text",
                                "text": PROMPT,
                            },
                        ],
                    }
                ],
            )
        texto = response.content[0].text
    except Exception:
        logger.exception("Error llamando a la API de Anthropic")
        return _resultado_vacio()

    # 5. Parsear la respuesta
    parsed = _parsear_json(texto)
    if parsed is None:
        return _resultado_vacio()

    # Partir de un resultado vacío y sobrescribir con lo que vino del modelo
    datos = _resultado_vacio()
    for clave in datos:
        if clave in parsed:
            datos[clave] = parsed[clave]

    # 6. Post-procesamiento: asegurar tipos numéricos o None
    datos["price_rmb"] = _a_numero(datos["price_rmb"])
    datos["qty_por_ctn"] = _a_numero(datos["qty_por_ctn"], entero=True)
    # largo/ancho/alto son las medidas de la CAJA FINAL, no del producto: el OCR
    # nunca las completa, se cargan a mano más adelante. Siempre vacías.
    datos["largo_cm"] = None
    datos["ancho_cm"] = None
    datos["alto_cm"] = None
    datos["cbm_directo"] = _a_numero(datos["cbm_directo"])
    datos["gw"] = _a_numero(datos["gw"])
    datos["cantidad_minima"] = _a_numero(datos["cantidad_minima"], entero=True)

    # confianza es obligatorio, nunca null
    if not datos.get("confianza"):
        datos["confianza"] = "baja"

    # legible debe ser booleano; ante cualquier valor raro, asumir no legible
    datos["legible"] = datos.get("legible") is True
    if datos["legible"]:
        datos["motivo_ilegible"] = None

    # 7. Resultado final
    return datos
