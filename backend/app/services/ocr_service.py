import base64
import json
import logging
import re

from anthropic import AsyncAnthropic

from app.core.config import settings
from app.core.ocr_limiter import slot_ocr
from app.services.recorte_service import GIRO_SEGUN_TEXTO, recuadro_valido

logger = logging.getLogger(__name__)

# Modelo de visión a utilizar.
# Opus 5 lee imágenes de hasta 2576px de lado largo (Opus 4.5 se quedaba en 1568)
# y entiende mucho mejor documentos y texto manuscrito: es lo que hace la diferencia
# leyendo carteles en chino escritos a mano y con brillos.
MODELO = "claude-opus-5"

# Cuánto "piensa" el modelo antes de responder. En Opus 5 el pensamiento va prendido
# por defecto y sale del mismo presupuesto de MAX_TOKENS. Si el OCR se equivoca leyendo
# carteles difíciles, subir a "high"; si sale caro o lento, bajar a "low".
ESFUERZO = "medium"

# Tope de tokens de la respuesta. Incluye el pensamiento del modelo, no solo el JSON:
# con el tope viejo de 1024 la respuesta se cortaba a la mitad y no se podía parsear.
MAX_TOKENS = 4096

# Motivo que se guarda cuando la foto NO se pudo procesar por un fallo NUESTRO
# (la API no respondió, se quedó sin crédito, devolvió algo ilegible...). Es distinto
# de que la foto esté borrosa: la vendedora no tiene nada que corregir y volver a
# tomarla no sirve de nada. El 15-ago-2026 la cuenta de Anthropic se quedó sin saldo
# y la app le dijo "foto no legible, vuelve a tomarla" 268 veces seguidas.
MOTIVO_ERROR_SISTEMA = "error_sistema"

# Caso concreto y de lejos el más común: la cuenta de Anthropic se quedó sin saldo.
# Se separa del error genérico porque la solución es distinta y concreta —recargar—
# y porque decir "error del sistema" manda a buscar un bug que no existe.
MOTIVO_SIN_SALDO = "sin_saldo"

_MOTIVOS_DE_SISTEMA = {MOTIVO_ERROR_SISTEMA, MOTIVO_SIN_SALDO}


def es_error_sistema(datos: dict | None) -> bool:
    """¿El resultado viene de un fallo NUESTRO (y no de una foto mala)?"""
    return bool(datos) and datos.get("motivo_ilegible") in _MOTIVOS_DE_SISTEMA


def _motivo_de_la_excepcion(exc: Exception) -> str:
    """Traduce el fallo de la API al motivo que verá la vendedora."""
    texto = str(exc).lower()
    # La API responde 400 con "your credit balance is too low to access the
    # Anthropic API". Es un mensaje estable de Anthropic; si algún día cambia, el
    # peor caso es caer al error genérico, que sigue siendo correcto.
    if "credit balance" in texto or "insufficient credit" in texto:
        return MOTIVO_SIN_SALDO
    return MOTIVO_ERROR_SISTEMA

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
  "colores": "colores o variantes disponibles como string separado por comas o null",
  "cantidad_minima": número entero de la mínima cantidad de compra DE ESTE PRODUCTO o null,
  "cantidad_minima_tienda": número entero de la mínima de compra de TODA LA TIENDA (sumando todos sus productos) o null,
  "notas": "cualquier otra información relevante o null",
  "hacia_donde_mira_el_texto": "arriba", "abajo", "izquierda" o "derecha": hacia qué borde de la foto apunta la PARTE DE ARRIBA de las letras,
  "recuadro_cartel": [x0, y0, x1, y1] con el recuadro del CARTEL o tablero de datos que acabas de leer, en fracciones de 0 a 1 (0,0 = esquina superior izquierda; 1,1 = inferior derecha), o null si no hay cartel,
  "recuadro_producto": [x0, y0, x1, y1] con el recuadro del PRODUCTO, en las mismas coordenadas,
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

• CANTIDAD MÍNIMA de compra. OJO: hay DOS mínimos distintos y muchos carteles traen los dos.
  Rótulos, en cualquiera de los tres idiomas:
  - español/inglés con ortografía manuscrita: "MOQ", "MQT", "MOA", "MOG", "MQO", "MINIMO", "MIN", "MIN ORDER", "MIN. QTY", "MINIMUM"
  - chino: "起订量", "起訂量", "最少", "最低", "最低起订", "起批", "最少订购", y "一手" (en Yiwu "una mano" es la unidad mínima de compra: si dice "一手10个" la mínima es 10)

  → cantidad_minima = el mínimo DE ESTE PRODUCTO. Es el que va acompañado de "por modelo",
    "x modelo", "por referencia", "each model", "per model", "每款", "每个款式" — o el único
    que hay cuando el cartel trae uno solo (ej: "MOQ: 600" → 600 ; "moa 10" → 10 ; "起订量 20" → 20).

  → cantidad_minima_tienda = el mínimo para comprarle A LA TIENDA en total, sumando todos sus
    productos. Va acompañado de "toda tienda", "x tienda", "por tienda", "total", "whole shop",
    "per shop", "全店", "整店" (ej: "Toda tienda MOQ: 10 cajas" → 10 ; "moq: 5 x tienda" → 5).

  Si el cartel trae los dos (ej: "MOQ: 2 cajas por modelo" y abajo "Toda tienda MOQ: 10 cajas"),
  devuelve LOS DOS: cantidad_minima=2 y cantidad_minima_tienda=10. Si solo trae uno y no dice si
  es por modelo o por tienda, ponlo en cantidad_minima y deja cantidad_minima_tienda en null.
  NUNCA repitas el mismo número en los dos campos.

• PESO BRUTO: NO se captura en esta etapa. Ignora por completo "PESO BRUTO", "P. BRUTO", "G.W.", "GROSS WEIGHT", "KGS", "毛重", "重量", "公斤" y su número: ese dato se toma después, al inspeccionar el producto, y no va en ningún campo del JSON.
  Por eso, un rótulo que empieza por "P" seguido de un número es SIEMPRE el PRECIO (price_rmb): en la letra manuscrita de estos carteles "Precio" y "Peso" se parecen muchísimo, y el precio está en casi todos los carteles.

• TIENDA / PROVEEDOR → supplier_nombre. Variantes:
  - español/inglés: "TIENDA", "TIENDA:", "BOOTH", "BOOTH NO.", "STAND", "SHOP", "STALL"
  - chino: "摊位", "攤位", "商位", "展位", "店铺", "铺号", "档口"
  - o directamente un CÓDIGO de stand tipo "F1-10968", "G3-17951", "Fr-2406"
  Va SIEMPRE en supplier_nombre (aunque sea un código), NUNCA en supplier_numero. Si en el tablero NO hay TIENDA pero hay una TARJETA DE VISITA del proveedor, usa el nombre de la tarjeta (ej: "CHIBAO" / "驰豹") para supplier_nombre y el teléfono para supplier_numero (en las tarjetas chinas el teléfono viene rotulado "电话", "手机" o "TEL").

• Puede haber otros rótulos: "DESCRIPCION" (texto libre del producto; en inglés "DESCRIPTION" / "ITEM", en chino "品名", "名称", "产品"), "TAMAÑO"/medidas (ej "20x10x9"; en inglés "SIZE", en chino "尺寸", "规格"), "LOGO", colores/variantes (ej "PLATA/TIRA/CADENA"; en inglés "COLOR", en chino "颜色", "色"). Usa la descripción y los colores si ayudan, pero NO pongas las medidas en largo/ancho/alto.

ORIENTACIÓN — las fotos del mercado salen giradas todo el tiempo, porque se toman con el celular de costado o parándose al lado del producto. En la cotización que recibe el cliente eso se ve mal, así que el sistema las endereza. Para eso necesita saber cómo está parado el texto.

NO calcules cuánto hay que girar la foto. Solo MIRA y responde una cosa: en las letras del cartel, la parte de ARRIBA de cada letra (el techo de la A, el punto de la i, lo que queda arriba cuando el texto está derecho), ¿hacia qué borde de la foto está apuntando?

hacia_donde_mira_el_texto:
- "arriba"    = el texto se lee normal, de izquierda a derecha. La foto ya está derecha.
- "derecha"   = el texto corre hacia abajo por la foto y para leerlo hay que inclinar la cabeza hacia la izquierda.
- "izquierda" = el texto corre hacia arriba por la foto y para leerlo hay que inclinar la cabeza hacia la derecha.
- "abajo"     = el texto está de cabeza, se lee al revés.

Si no hay texto legible, fíjate en el producto: hacia dónde apunta su parte de arriba, la que queda arriba cuando está apoyado como se usa. Si no puedes decidirlo, responde "arriba".

RECUADROS — además de leer los datos, tienes que marcar DÓNDE está cada cosa en la foto. Sirve para recortar la imagen y que en la cotización del cliente y en el pedido al proveedor salga SOLO el producto, sin el cartel. Es tan importante como leer los datos: no lo saltes.

Las coordenadas van en fracciones de 0 a 1, como [x0, y0, x1, y1]: x0/y0 es la esquina superior izquierda del recuadro y x1/y1 la inferior derecha. El origen (0,0) es la esquina superior izquierda de la foto. Ejemplo: algo que ocupa la mitad derecha y la mitad de abajo sería [0.5, 0.5, 1.0, 1.0].

• recuadro_cartel = dónde está el cartel, tablero, tarjeta o papel del que acabas de leer los datos. Si los datos estaban escritos directamente sobre el piso o la mesa, encuadra esa zona escrita. Acabas de leerlo, así que sabes exactamente dónde está: márcalo SIEMPRE que haya leído algo.

• recuadro_producto = dónde está el producto que se está cotizando, o sea TODO LO QUE NO ES EL CARTEL. Piénsalo así: quita el cartel de la foto y lo que queda es el producto. Casi siempre están separados, uno arriba y el otro abajo, o uno a cada lado.
  - PEGA el recuadro a los bordes del producto. Que sea ajustado: si adentro del recuadro queda mucha mesa, piso o pared vacia, achicalo hasta que sobre poco. El aire se lo agrega despues el sistema.
  - Al mismo tiempo, no cortes el producto: si dudas entre dejar afuera una parte o incluir un poco de mesa, incluye la mesa.
  - Deja fuera el cartel, la tarjeta del proveedor, las manos, el piso vacío y la mesa vacía.
  - Si hay varias unidades del MISMO producto juntas (un exhibidor, una pila, una caja abierta con su contenido), encuádralas todas como un solo bloque.
  - Si hay productos vecinos que claramente no son el que se cotiza, déjalos fuera.

REGLA IMPORTANTE: si pudiste leer el cartel, ENTONCES devuelve los dos recuadros. Que el producto sea chico, que esté de costado, que la foto tenga brillos o que no sepas exactamente qué producto es NO son motivos para devolver null: igual sabes qué parte de la foto NO es el cartel, y eso es lo que hay que marcar. Un recuadro aproximado sirve; null no sirve para nada.

Devuelve recuadro_producto en null SOLO en dos casos: cuando la foto es ilegible (legible=false), o cuando el producto y el cartel están tan encimados que no se pueden separar.

Reglas:
- SIEMPRE identifica el producto y completa descripcion_es y descripcion_en mirando la foto, aunque el cartel no traiga descripción. Debe ser específica del producto que ves, no genérica.
- material y uso: infiérelos de la imagen aunque no estén escritos; si no puedes deducirlo, null.
- Si un dato NUMÉRICO no aparece, usa null; nunca inventes números. Pero si en el tablero SÍ está el precio, las piezas por caja, el CBM o la cantidad mínima (en cualquiera de sus variantes de arriba), DEBES extraerlos: no los dejes en null.
- largo_cm, ancho_cm y alto_cm van SIEMPRE en null: son las medidas de la CAJA FINAL, que se cargan a mano después. Aunque el cartel muestre medidas (ej "28x23x12"), NO las pongas ahí.
- price_rmb, qty_por_ctn, cbm_directo, cantidad_minima, cantidad_minima_tienda deben ser números (float o int) o null, nunca strings.
- confianza es obligatorio, nunca null.
- Que el cartel esté escrito en chino o en inglés NO es motivo para marcar legible=false ni para bajar la confianza: los tres idiomas son igual de válidos y sus datos deben extraerse igual.
- legible es obligatorio, nunca null: evalúa SOLO si se puede LEER el texto. Un reflejo/brillo o que la foto esté rotada NO la hacen ilegible por sí solos. Marca legible=false SOLO si el texto realmente no se distingue (muy borroso, movido, muy oscuro, tapado o cortado). Ante la duda por buena calidad, marca true.
"""

# Se agrega al PROMPT base SOLO cuando la cotización es de bolsos/carteras: un
# bolso necesita más rigor que un producto genérico (tamaño, empaque, etiqueta,
# herrajes, riata) y un mínimo de compra que puede ser de LA TIENDA (no del
# modelo puntual), que a su vez puede venir de dos formas.
PROMPT_BOLSOS_EXTRA = """

ESTE PRODUCTO ES UN BOLSO/CARTERA — además de las claves de arriba, el JSON debe
traer también estas, con la misma exigencia de leer los tres idiomas:

{
  "tamano": "tamaño o dimensiones del bolso tal como aparecen en el cartel (ej: 'GRANDE', 'M', '30x20x10') o null",
  "empaque": "cómo viene empacado (ej: 'bolsa individual', 'caja', 'con relleno') o null",
  "etiqueta": "qué etiqueta o marca lleva el bolso (ej: 'con etiqueta de tela', 'sin marca', el nombre de una marca) o null",
  "herrajes": "material/color de los herrajes (hebillas, argollas, cierres, remaches) que veas en la foto o que diga el cartel (ej: 'dorado', 'plateado', 'níquel') o null",
  "riata": "descripción de la riata/correa/asa (ej: 'ajustable', 'cadena', 'cuero sintético', 'desmontable') o null",
  "minimo_cajas_tienda": número entero del mínimo de CAJAS que exige la tienda en total (sin importar cuántas piezas trae cada una) o null,
  "minimo_piezas_caja_tienda": número entero del mínimo de PIEZAS POR CAJA que exige la tienda (cuando el mínimo viene como "cajas + piezas por caja", no solo cajas) o null
}

Rótulos típicos para el mínimo de la TIENDA (distinto de cantidad_minima/cantidad_minima_tienda de arriba, que son por producto): "MIN CAJAS TIENDA", "MINIMO TIENDA", chino "全店起订箱数". Si el cartel dice, por ejemplo, "mínimo 5 cajas" sin más, es minimo_cajas_tienda=5 y minimo_piezas_caja_tienda=null. Si dice "mínimo 5 cajas de 10 piezas", es minimo_cajas_tienda=5 y minimo_piezas_caja_tienda=10. Si el cartel no menciona nada de esto, deja los dos en null: no lo inventes ni lo confundas con cantidad_minima.

Para tamano, empaque, etiqueta, herrajes y riata: si el cartel no trae el dato por escrito, mira la foto e infiere lo que puedas (por ejemplo los herrajes casi siempre se ven); si de verdad no se puede saber ni leyendo ni mirando, deja null.
"""


def _resultado_vacio(motivo: str = "no_procesada") -> dict:
    """Resultado con todos los campos en null. `motivo` distingue si fue un fallo
    del sistema (MOTIVO_ERROR_SISTEMA) o una foto que no se pudo leer."""
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
        "colores": None,
        "cantidad_minima": None,
        "cantidad_minima_tienda": None,
        # Solo se piden/completan en modo bolsos; en una cotización de productos
        # varios quedan siempre en None (el prompt base no las menciona).
        "tamano": None,
        "empaque": None,
        "etiqueta": None,
        "herrajes": None,
        "riata": None,
        "minimo_cajas_tienda": None,
        "minimo_piezas_caja_tienda": None,
        "notas": None,
        "hacia_donde_mira_el_texto": None,
        "giro_necesario": 0,
        "recuadro_cartel": None,
        "recuadro_producto": None,
        # URL del recorte ya subido (lo completa el backend, no el modelo)
        "foto_recorte_url": None,
        "confianza": "baja",
        # Si no se pudo procesar la foto, se considera no legible: la vendedora
        # deberá volver a tomarla.
        "legible": False,
        "motivo_ilegible": motivo,
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


async def extraer_datos_etiqueta(
    imagen_bytes: bytes, media_type: str, tipo_cotizacion: str = "productos"
) -> dict:
    """Extrae datos de una etiqueta de proveedor usando Claude Vision.

    `tipo_cotizacion` "bolsos" agrega al prompt base el bloque de campos
    propios de bolsos (tamaño, empaque, herrajes, riata, mínimos de tienda);
    el prompt de productos varios no se toca.

    Nunca lanza excepciones: ante cualquier fallo devuelve un resultado vacío
    con confianza baja.
    """
    prompt = PROMPT + PROMPT_BOLSOS_EXTRA if tipo_cotizacion == "bolsos" else PROMPT

    # 1. Imagen a base64
    base64_string = base64.standard_b64encode(imagen_bytes).decode("utf-8")

    # 2-4. Llamada a la API de Anthropic (cliente único + tope global de concurrencia
    # respaldado por Postgres, válido aun con varias réplicas).
    try:
        client = _get_client()
        async with slot_ocr():
            response = await client.messages.create(
                model=MODELO,
                max_tokens=MAX_TOKENS,
                output_config={"effort": ESFUERZO},
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
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )
        # El primer bloque ya no es necesariamente el texto: con el pensamiento
        # prendido la respuesta trae bloques de tipo "thinking" antes. Se busca el
        # primer bloque de texto en vez de asumir la posición 0.
        texto = next((b.text for b in response.content if b.type == "text"), "")
        if not texto:
            logger.error(
                "La respuesta del OCR no trae texto (stop_reason=%s)", response.stop_reason
            )
            return _resultado_vacio(MOTIVO_ERROR_SISTEMA)
    except Exception as exc:
        logger.exception("Error llamando a la API de Anthropic")
        return _resultado_vacio(_motivo_de_la_excepcion(exc))

    # 5. Parsear la respuesta
    parsed = _parsear_json(texto)
    if parsed is None:
        # El modelo respondió pero no en JSON: tampoco es culpa de la foto.
        logger.error("La respuesta del OCR no es JSON válido")
        return _resultado_vacio(MOTIVO_ERROR_SISTEMA)

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
    datos["cantidad_minima"] = _a_numero(datos["cantidad_minima"], entero=True)
    datos["cantidad_minima_tienda"] = _a_numero(datos["cantidad_minima_tienda"], entero=True)
    # El mismo número en los dos campos no aporta nada y confundiría a la vendedora
    # con un aviso falso de "hay dos mínimos".
    if datos["cantidad_minima_tienda"] == datos["cantidad_minima"]:
        datos["cantidad_minima_tienda"] = None
    datos["minimo_cajas_tienda"] = _a_numero(datos["minimo_cajas_tienda"], entero=True)
    datos["minimo_piezas_caja_tienda"] = _a_numero(datos["minimo_piezas_caja_tienda"], entero=True)

    # En bolsos hay un solo mecanismo de "mínimo de toda la tienda": el nuevo par
    # minimo_cajas_tienda/minimo_piezas_caja_tienda (siempre en cajas). El mecanismo
    # genérico cantidad_minima_tienda es para productos varios (en piezas) y mostrar
    # los dos a la vez confunde con dos avisos de "mínimo de tienda" distintos: si el
    # cartel trae el patrón "por modelo / por tienda", el de tienda se vuelca acá.
    if tipo_cotizacion == "bolsos":
        if datos["minimo_cajas_tienda"] is None and datos["cantidad_minima_tienda"] is not None:
            datos["minimo_cajas_tienda"] = datos["cantidad_minima_tienda"]
        datos["cantidad_minima_tienda"] = None

    # Se le pide una observacion ("hacia donde apunta el techo de las letras") y
    # el giro se calcula aca. Pedirle directamente los grados salia mal: contesta
    # el sentido contrario y la foto quedaba de cabeza en el PDF del cliente.
    datos["giro_necesario"] = GIRO_SEGUN_TEXTO.get(
        str(datos.get("hacia_donde_mira_el_texto") or "").strip().lower(), 0
    )

    datos["recuadro_cartel"] = recuadro_valido(datos.get("recuadro_cartel"), area_maxima=0.98)
    datos["recuadro_producto"] = recuadro_valido(datos.get("recuadro_producto"))
    # Queda registrado para poder revisar despues por que una foto no se recorto
    logger.info(
        "OCR recuadros: producto=%s cartel=%s texto_mira=%s giro=%s legible=%s",
        datos["recuadro_producto"], datos["recuadro_cartel"],
        datos["hacia_donde_mira_el_texto"], datos["giro_necesario"], datos["legible"],
    )

    # confianza es obligatorio, nunca null
    if not datos.get("confianza"):
        datos["confianza"] = "baja"

    # legible debe ser booleano; ante cualquier valor raro, asumir no legible
    datos["legible"] = datos.get("legible") is True
    if datos["legible"]:
        datos["motivo_ilegible"] = None

    # 7. Resultado final
    return datos
