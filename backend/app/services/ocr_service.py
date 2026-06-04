import asyncio
import base64
import json
import re

from anthropic import AsyncAnthropic

from app.core.config import settings

# Modelo de visión a utilizar
MODELO = "claude-opus-4-5-20251101"

# Cliente único reutilizado (evita abrir una conexión nueva por cada foto).
# max_retries: el SDK reintenta con backoff exponencial ante 429 / 5xx / errores de red.
_client: AsyncAnthropic | None = None

# Tope GLOBAL de llamadas de visión en simultáneo en todo el proceso.
# Aunque 20 vendedoras disparen lotes a la vez, nunca habrá más de N llamadas
# concurrentes a Anthropic: el resto se encola. Protege rate limits y conexiones.
_ocr_semaphore: asyncio.Semaphore | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            max_retries=settings.OCR_MAX_RETRIES,
        )
    return _client


def _get_semaphore() -> asyncio.Semaphore:
    # Se crea de forma perezosa dentro del event loop en ejecución.
    global _ocr_semaphore
    if _ocr_semaphore is None:
        _ocr_semaphore = asyncio.Semaphore(settings.OCR_CONCURRENCIA_GLOBAL)
    return _ocr_semaphore

# Prompt fijo enviado a Claude Vision (no configurable desde la UI)
PROMPT = """
Eres un experto en leer etiquetas de precios de proveedores del mercado de Yiwu, China.
Analiza esta imagen y extrae los datos que puedas encontrar.
Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, sin bloques de código, sin comillas adicionales.

El JSON debe tener exactamente estas claves:
{
  "supplier_nombre": "nombre de la tienda o empresa (string o null)",
  "supplier_numero": "número de stand o booth (string o null)",
  "price_rmb": número decimal del precio en yuan o null,
  "qty_por_ctn": número entero de piezas por caja o null,
  "largo_cm": número decimal del largo en cm o null,
  "ancho_cm": número decimal del ancho en cm o null,
  "alto_cm": número decimal del alto en cm o null,
  "cbm_directo": número decimal si hay CBM ya calculado en la etiqueta o null,
  "gw": número decimal del peso bruto por caja en kg o null,
  "colores": "colores disponibles como string separado por comas o null",
  "cantidad_minima": número entero de cantidad mínima de pedido o null,
  "descripcion_zh": "descripción del producto en chino si aparece o null",
  "notas": "cualquier otra información relevante o null",
  "confianza": "alta, media o baja según tu certeza en la extracción"
}

Reglas:
- Si un campo no aparece en la imagen usa null, nunca inventes datos
- price_rmb, qty_por_ctn, largo_cm, ancho_cm, alto_cm, cbm_directo, gw, cantidad_minima deben ser números (float o int) o null, nunca strings
- confianza es obligatorio, nunca null
"""


def _resultado_vacio() -> dict:
    """Devuelve un resultado con todos los campos en null y confianza baja"""
    return {
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
        "descripcion_zh": None,
        "notas": None,
        "confianza": "baja",
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

    # 2-4. Llamada a la API de Anthropic (cliente único + tope global de concurrencia)
    try:
        client = _get_client()
        async with _get_semaphore():
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
    except Exception as e:
        print(f"Error llamando a la API de Anthropic: {e}")
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
    datos["largo_cm"] = _a_numero(datos["largo_cm"])
    datos["ancho_cm"] = _a_numero(datos["ancho_cm"])
    datos["alto_cm"] = _a_numero(datos["alto_cm"])
    datos["cbm_directo"] = _a_numero(datos["cbm_directo"])
    datos["gw"] = _a_numero(datos["gw"])
    datos["cantidad_minima"] = _a_numero(datos["cantidad_minima"], entero=True)

    # Calcular CBM a partir de las dimensiones si no vino directo
    if datos["cbm_directo"] is None and None not in (
        datos["largo_cm"],
        datos["ancho_cm"],
        datos["alto_cm"],
    ):
        datos["cbm_directo"] = round(
            datos["largo_cm"] * datos["ancho_cm"] * datos["alto_cm"] / 1_000_000, 6
        )

    # confianza es obligatorio, nunca null
    if not datos.get("confianza"):
        datos["confianza"] = "baja"

    # 7. Resultado final
    return datos
