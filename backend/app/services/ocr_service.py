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

MUY IMPORTANTE — los datos vienen escritos a mano, con letra irregular, abreviaturas y a veces errores de ortografía. El texto PUEDE ESTAR ROTADO (de costado 90°, o 180°) porque la foto se tomó girada: LÉELO igual, gira mentalmente la imagen si hace falta. Los tableros blancos suelen tener REFLEJOS/BRILLOS de la luz: esfuérzate en leer a través del brillo. Reconoce SIEMPRE estos datos, con TODAS sus variantes:

• PRECIO unitario (yuan/RMB) → price_rmb. Aparece como:
  - la palabra "PRECIO", "PRECIO:", "P:"
  - un número precedido por el símbolo YUAN "¥" o "￥" o "元" o "RMB" o una "Y" suelta (ej: "¥22" → 22 ; "¥ 12.8" → 12.8 ; "PRECIO: 17" → 17)
  Cualquiera de esas formas ES el precio unitario.

• PIEZAS/UNIDADES por CAJA (cartón) → qty_por_ctn. Aparece como cualquiera de estos rótulos, con o sin dos puntos, y el número puede ir ANTES o DESPUÉS:
  - "CX", "CAJA X", "CAJAX", "CJ X", "C/X", "X/CAJA"
  - "PCS", "PC", "PZ", "PZS", "PIEZAS", "UNID", "U/CAJA"
  Ejemplos: "CX: 200" → 200 ; "CAJA X: 120" → 120 ; "200 PCS" → 200 ; "pcs 30" → 30

• CBM (cubicaje/volumen por caja) → cbm_directo. Variantes: "CBM", "CMB" (letras invertidas, es lo mismo), con o sin dos puntos (ej: "CBM: 0.22" → 0.22 ; "cbm 0.11" → 0.11)

• CANTIDAD MÍNIMA de compra → cantidad_minima. Rótulo con variantes de ortografía manuscrita: "MOQ", "MQT", "MOA", "MOG", "MQO", "MINIMO", "MIN" (la "Q" manuscrita a veces parece "A" o "G"). Extrae SOLO el número aunque diga "10 cajas" o "5 x tienda" (ej: "MOQ: 600" → 600 ; "moa 10" → 10 ; "moq: 5 x tienda" → 5)

• TIENDA / PROVEEDOR → supplier_nombre. Aparece como "TIENDA", "TIENDA:", o directamente un CÓDIGO de stand tipo "F1-10968", "G3-17951", "Fr-2406". Va SIEMPRE en supplier_nombre (aunque sea un código), NUNCA en supplier_numero. Si en el tablero NO hay TIENDA pero hay una TARJETA DE VISITA del proveedor, usa el nombre de la tarjeta (ej: "CHIBAO" / "驰豹") para supplier_nombre y el teléfono para supplier_numero.

• Puede haber otros rótulos: "DESCRIPCION" (texto libre del producto), "TAMAÑO"/medidas (ej "20x10x9"), "LOGO", colores/variantes (ej "PLATA/TIRA/CADENA"). Usa la descripción y los colores si ayudan, pero NO pongas las medidas en largo/ancho/alto.

Reglas:
- SIEMPRE identifica el producto y completa descripcion_es y descripcion_en mirando la foto, aunque el cartel no traiga descripción. Debe ser específica del producto que ves, no genérica.
- material y uso: infiérelos de la imagen aunque no estén escritos; si no podés deducirlo, null.
- Si un dato NUMÉRICO no aparece, usa null; nunca inventes números. Pero si en el tablero SÍ está el precio, las piezas por caja, el CBM o la cantidad mínima (en cualquiera de sus variantes de arriba), DEBES extraerlos: no los dejes en null.
- largo_cm, ancho_cm y alto_cm van SIEMPRE en null: son las medidas de la CAJA FINAL, que se cargan a mano después. Aunque el cartel muestre medidas (ej "28x23x12"), NO las pongas ahí.
- price_rmb, qty_por_ctn, cbm_directo, gw, cantidad_minima deben ser números (float o int) o null, nunca strings.
- confianza es obligatorio, nunca null.
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


def _a_numero(valor, entero: bool = False):
    """Convierte un valor a número (o None). Extrae el número si viene como string"""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return int(valor) if entero else float(valor)
    if isinstance(valor, str):
        coincidencia = re.search(r"-?\d+(?:\.\d+)?", valor.replace(",", ""))
        if not coincidencia:
            return None
        numero = float(coincidencia.group())
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
