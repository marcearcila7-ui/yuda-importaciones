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
Eres un experto en productos del mercado mayorista de Yiwu, China.
En la imagen hay UN PRODUCTO y, normalmente, un cartel/tablero o etiqueta con su descripción, precio y datos.

Tu tarea tiene DOS partes y debes combinarlas:
1. IDENTIFICA visualmente qué producto es mirando la foto (qué es, de qué material parece, para qué sirve).
2. LEE el cartel/tablero/etiqueta y extrae los datos escritos (precio, proveedor, medidas, etc.).

Responde ÚNICAMENTE con un objeto JSON válido, sin texto antes ni después, sin bloques de código, sin comillas adicionales.

El JSON debe tener exactamente estas claves:
{
  "descripcion_es": "qué es el producto, en español, claro y específico (ej: 'Vaso plástico con tapa y sorbete') o null",
  "descripcion_en": "lo mismo en inglés (ej: 'Plastic cup with lid and straw') o null",
  "descripcion_zh": "lo mismo en chino, o lo que diga el cartel en chino, o null",
  "material": "material principal que ves (plástico, metal, vidrio, cerámica, tela, madera, silicona, papel...) o null",
  "uso": "categoría o uso del producto (cocina, hogar, juguete, oficina, baño, decoración, mascotas...) o null",
  "supplier_nombre": "nombre de la tienda o empresa (string o null)",
  "supplier_numero": "número de stand o booth (string o null)",
  "price_rmb": número decimal del PRECIO unitario en yuan/RMB o null,
  "qty_por_ctn": número entero de piezas por caja (CX / unidades por cartón) o null,
  "largo_cm": null (SIEMPRE null),
  "ancho_cm": null (SIEMPRE null),
  "alto_cm": null (SIEMPRE null),
  "cbm_directo": número decimal del CBM (cubicaje/volumen por caja) si la etiqueta lo trae ya calculado o null,
  "gw": número decimal del peso bruto por caja en kg o null,
  "colores": "colores disponibles como string separado por comas o null",
  "cantidad_minima": número entero del MQT = mínima cantidad de CAJAS (cartones) que exige el proveedor para comprar o null,
  "notas": "cualquier otra información relevante o null",
  "confianza": "alta, media o baja según tu certeza en la extracción",
  "legible": true o false (booleano) — true SOLO si la foto se ve bien y se puede leer el cartel; false si la imagen está borrosa, movida, sobreexpuesta (quemada por la luz), muy oscura, con reflejos/sombras que tapan el texto, o si no se distingue el producto,
  "motivo_ilegible": "si legible es false, describe brevemente el problema en una palabra o dos (ej: 'borrosa', 'sobreexpuesta', 'oscura', 'reflejo', 'recortada'); si legible es true, null"
}

MUY IMPORTANTE — el tablero/pizarra escrito a mano usa estas etiquetas (en español, manuscritas). Reconócelas SIEMPRE, aunque la letra sea irregular:
- "PRECIO" (o "PRECIO:") → price_rmb. Ej: "PRECIO: 12.8" → 12.8
- "CX" → qty_por_ctn (cantidad de piezas por caja). Ej: "CX: 100" → 100
- "CBM" o "CMB" (a veces escriben las letras al revés, ambas significan lo mismo: el cubicaje/volumen por caja) → cbm_directo. Ej: "CMB: 0.072" → 0.072
- "MQT" o "MOQ" (sinónimos) → cantidad_minima (mínima cantidad de CAJAS que pide el proveedor). Si dice "MQT: 10 CAJAS" extrae solo el número: 10
- "TIENDA" (o "TIENDA:") → supplier_nombre. Es el nombre o CÓDIGO de la tienda/proveedor tal como está escrito, aunque sea un código tipo "Fr-2406" o "F1-906". Va SIEMPRE en supplier_nombre, NUNCA en supplier_numero.
- supplier_numero es solo el número de stand/booth si aparece aparte (distinto de la TIENDA). Si solo hay "TIENDA", deja supplier_numero en null.
- A veces hay una tarjeta de visita del proveedor: usa su nombre para supplier_nombre y el número de stand/dirección para supplier_numero.

Reglas:
- SIEMPRE identifica el producto y completa descripcion_es y descripcion_en mirando la foto, aunque el cartel no traiga descripción.
- La descripción debe ser útil y específica del producto que ves, no genérica.
- material y uso: infiérelos de la imagen aunque no estén escritos; si realmente no podés deducirlo, usa null.
- Si un dato NUMÉRICO (precio, medidas, peso) no aparece, usa null; nunca inventes números.
- Pero si en el tablero SÍ aparecen PRECIO, CX, CBM/CMB o MQT, DEBES extraerlos (no los dejes en null).
- largo_cm, ancho_cm y alto_cm van SIEMPRE en null: NO corresponden a las medidas del producto sino a las de la CAJA FINAL, que se cargan a mano después. Aunque el cartel muestre medidas (ej "28x23x12"), NO las pongas en esos campos.
- price_rmb, qty_por_ctn, cbm_directo, gw, cantidad_minima deben ser números (float o int) o null, nunca strings.
- confianza es obligatorio, nunca null.
- legible es obligatorio, nunca null: evalúa SOLO la calidad de la foto para poder leerla, no si trae todos los datos. Si dudas por mala calidad de imagen, marca false.
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
