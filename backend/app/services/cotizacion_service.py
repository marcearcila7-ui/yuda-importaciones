import base64
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
from openpyxl.drawing.xdr import XDRPositiveSize2D
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins
from openpyxl.utils.units import pixels_to_EMU
from app.services.imagen_service import CALIDAD_JPEG
from app.services.pdf_service import render_pdf

from app.models.sesion import Sesion

logger = logging.getLogger(__name__)

# Foto principal y fotos de detalle van al MISMO tamaño: antes las de detalle
# salían minúsculas (22px) y era imposible distinguir nada en ellas, dando a
# entender que un recorte ya hecho no servía de nada. El cliente y la agencia
# de carga necesitan poder ver el detalle tan bien como la foto principal.
LADO_FOTO_CLIENTE = 95
GAP_FOTO_CLIENTE = 6

# Datos de contacto de YUDA (hardcodeados en el documento)
CONTACTO = {
    "dir_china": "Room 0909-0911, Building A, Futian Building, No.1121, Chouzhou North Road, Yiwu City, China. Zip: 322023",
    "dir_colombia": "Cr 53 cll 45-115 piso 8 Edificio Multivariedades, Centro de Medellín",
    "email": "contacto@yudaimportaciones.com",
    "telefono": "+57 123 456 78 90",
    "web": "yudaimportaciones.com",
    "razon": "义乌市与达贸易有限公司 · YIWU YUDA TRADING CO.,LTD",
}

# Aviso que exige la agencia de carga, tal cual va en su formato. Se muestra
# arriba de todo y en los dos idiomas: sin estos datos no cargan la mercancia.
# En este negocio todo se vende por piezas: la columna existe porque el formato
# de la agencia la pide, pero nunca cambia.
UNIDAD = "PCS"

AVISO_AGENCIA = [
    "备注：1，麻烦严格按照下面要求填写产品信息，如因资料不完整不能及时装柜，请谅解。 "
    "Requisito indispensable la elaboración de la lista de empaque con la información requerida "
    "al entregar la mercancía: no se cargará mercancía sin las descripciones mínimas e "
    "información completa del producto y la foto real del artículo.",
    "2，如果是机器，大型电器类的，还需要提供产品的技术参数表-型号-序列号-货号-牌字。 "
    "PARA EL ENVÍO DE MÁQUINAS Y ARTÍCULOS ELECTRÓNICOS SE DEBE APORTAR POR OBLIGACIÓN: "
    "FICHA TÉCNICA DE FÁBRICA, MODELO, SERIE, REFERENCIA Y MARCA.",
]

# Etiquetas por idioma
LABELS = {
    "es": {
        "empresa": "YUDA IMPORTACIONES",
        "numero": "N° Cotización",
        "emision": "Fecha de emisión",
        "cliente": "Cliente",
        "totales": "TOTALES",
        "nota": "Los precios están sujetos a confirmación del proveedor.",
        "resumen": "RESUMEN:   {n} productos   ·   {cajas} cajas   ·   Total USD ${usd}   ·   Peso total {gw} kg   ·   CBM {cbm}",
    },
    "en": {
        "empresa": "YIWU YUDA TRADING CO.,LTD",
        "numero": "Quotation No.",
        "emision": "Issue date",
        "cliente": "Client",
        "totales": "TOTALS",
        "nota": "Prices are subject to supplier confirmation.",
        "resumen": "SUMMARY:   {n} products   ·   {cajas} boxes   ·   Total USD ${usd}   ·   Total weight {gw} kg   ·   CBM {cbm}",
    },
    "zh": {
        "empresa": "义乌市与达贸易有限公司",
        "numero": "报价单号",
        "emision": "签发日期",
        "cliente": "客户",
        "totales": "合计",
        "nota": "价格以供应商确认为准。",
        "resumen": "汇总：   {n} 件产品   ·   {cajas} 箱   ·   总计 USD ${usd}   ·   总毛重 {gw} kg   ·   CBM {cbm}",
    },
}

# Columnas de la cotización al cliente: clave estable (no cambia con el
# idioma) en el orden en que salen en el documento. La vendedora puede elegir
# cuáles mostrar antes de descargar (ExportarCotizacion en el frontend);
# "columnas" en generar_cotizacion_excel/pdf es la lista de claves elegidas.
CLAVES_COLUMNAS = [
    "numero", "fecha_recibo", "shipping_mark", "foto", "referencia", "codigo",
    "desc_es", "desc_en", "desc_zh", "material", "uso",
    "cajas", "uds_caja", "unidad", "cant_total",
    "precio_rmb", "total_rmb", "precio_usd", "total_usd",
    "largo", "ancho", "alto", "cbm", "t_cbm",
    "peso", "peso_total", "mqt", "marca",
]

# Propias de una cotización de bolsos (sesion.tipo_cotizacion == "bolsos"):
# solo se ofrecen como opción, y solo salen en el documento, cuando la
# cotización es de ese tipo. Van al final, después de las genéricas.
CLAVES_COLUMNAS_BOLSOS = [
    "tamano", "empaque", "etiqueta", "herrajes", "riata",
    "minimo_cajas_tienda", "minimo_piezas_caja_tienda",
]

# Sin foto o sin referencia el cliente no puede identificar qué está
# cotizando: no se pueden ocultar aunque la vendedora las desmarque.
COLUMNAS_OBLIGATORIAS = {"foto", "referencia"}

ETIQUETAS_COLUMNA = {
    "es": {
        "numero": "N°", "fecha_recibo": "Fecha de recibo", "shipping_mark": "Shipping mark",
        "foto": "Foto", "referencia": "Referencia", "codigo": "Código",
        "desc_es": "Descripción (Español)", "desc_en": "Description (English)", "desc_zh": "描述 (中文)",
        "material": "Material", "uso": "Uso",
        "cajas": "Cajas", "uds_caja": "Uds/Caja", "unidad": "Unidad", "cant_total": "Cantidad total",
        "precio_rmb": "Precio RMB", "total_rmb": "Total RMB", "precio_usd": "Precio USD", "total_usd": "Total USD",
        "largo": "Largo cm", "ancho": "Ancho cm", "alto": "Alto cm", "cbm": "CBM", "t_cbm": "T.CBM",
        "peso": "Peso kg", "peso_total": "Peso total kg", "mqt": "MQT (mín. cajas)", "marca": "Marca",
        "tamano": "Tamaño", "empaque": "Empaque", "etiqueta": "Etiqueta", "herrajes": "Herrajes",
        "riata": "Riata/correa", "minimo_cajas_tienda": "Mínimo cajas (tienda)",
        "minimo_piezas_caja_tienda": "Mínimo piezas por caja (tienda)",
    },
    "en": {
        "numero": "N°", "fecha_recibo": "Receipt date", "shipping_mark": "Shipping mark",
        "foto": "Photo", "referencia": "Reference", "codigo": "Code",
        "desc_es": "Descripción (Español)", "desc_en": "Description (English)", "desc_zh": "描述 (中文)",
        "material": "Material", "uso": "Use",
        "cajas": "Boxes", "uds_caja": "Units/Box", "unidad": "Unit", "cant_total": "Total quantity",
        "precio_rmb": "Price RMB", "total_rmb": "Total RMB", "precio_usd": "Price USD", "total_usd": "Total USD",
        "largo": "Length cm", "ancho": "Width cm", "alto": "Height cm", "cbm": "CBM", "t_cbm": "T.CBM",
        "peso": "Weight kg", "peso_total": "Total weight kg", "mqt": "MOQ (min. boxes)", "marca": "Brand",
        "tamano": "Size", "empaque": "Packaging", "etiqueta": "Label", "herrajes": "Hardware",
        "riata": "Strap", "minimo_cajas_tienda": "Minimum boxes (store)",
        "minimo_piezas_caja_tienda": "Minimum pieces per box (store)",
    },
    "zh": {
        "numero": "序号", "fecha_recibo": "收货日期", "shipping_mark": "唛头",
        "foto": "图片", "referencia": "参考号", "codigo": "货号",
        "desc_es": "描述 (西班牙语)", "desc_en": "描述 (英语)", "desc_zh": "描述 (中文)",
        "material": "材质", "uso": "用途",
        "cajas": "箱数", "uds_caja": "每箱数量", "unidad": "单位", "cant_total": "总数量",
        "precio_rmb": "单价(元)", "total_rmb": "总价(元)", "precio_usd": "单价(USD)", "total_usd": "总价(USD)",
        "largo": "长 cm", "ancho": "宽 cm", "alto": "高 cm", "cbm": "CBM", "t_cbm": "总CBM",
        "peso": "毛重kg", "peso_total": "总毛重kg", "mqt": "起订量(箱)", "marca": "品牌",
        "tamano": "尺寸", "empaque": "包装", "etiqueta": "标签", "herrajes": "五金件",
        "riata": "背带", "minimo_cajas_tienda": "最低箱数（全店）",
        "minimo_piezas_caja_tienda": "每箱最低件数（全店）",
    },
}


# Las columnas de solo números (cantidades, precios, medidas) no necesitan
# tanto ancho como el texto: un número siempre es corto y no se "lee mal" si
# la columna queda justa. Achicarlas es lo que le deja espacio real a las
# columnas de texto (descripciones, empaque, etc.), que sí lo necesitan.
ANCHOS_COLUMNA = {
    "numero": 4, "fecha_recibo": 11, "shipping_mark": 9, "foto": 30, "referencia": 11, "codigo": 10,
    "desc_es": 30, "desc_en": 30, "desc_zh": 24, "material": 13, "uso": 16,
    "cajas": 5, "uds_caja": 6, "unidad": 5, "cant_total": 8,
    "precio_rmb": 8, "total_rmb": 9, "precio_usd": 8, "total_usd": 9,
    "largo": 6, "ancho": 6, "alto": 6, "cbm": 7, "t_cbm": 7,
    "peso": 6, "peso_total": 8, "mqt": 7, "marca": 12,
    "tamano": 11, "empaque": 15, "etiqueta": 15, "herrajes": 12, "riata": 15,
    "minimo_cajas_tienda": 9, "minimo_piezas_caja_tienda": 9,
}


def _columnas_activas(columnas: list[str] | None, es_bolsos: bool = False) -> list[str]:
    """Filtra y ordena las columnas a mostrar en la cotización del cliente.

    Respeta siempre el orden canónico (CLAVES_COLUMNAS, + CLAVES_COLUMNAS_BOLSOS
    al final si `es_bolsos`), ignora claves que no existan o que no apliquen
    para este tipo de cotización, y agrega las obligatorias aunque no vengan
    elegidas. `columnas` en None (nadie eligió nada, ej. el portal del
    cliente) muestra todas las que apliquen."""
    disponibles = CLAVES_COLUMNAS + CLAVES_COLUMNAS_BOLSOS if es_bolsos else CLAVES_COLUMNAS
    if columnas is None:
        return list(disponibles)
    elegidas = set(columnas) | COLUMNAS_OBLIGATORIAS
    return [c for c in disponibles if c in elegidas]


def _valores_fila(n: int, item, calc: dict, sesion: Sesion) -> dict:
    """Valor de cada columna posible para una fila de la cotización del
    cliente. `foto` va en None: esa columna se llena aparte, como imagen."""
    return {
        "numero": n,
        "fecha_recibo": item.fecha_recibo,
        "shipping_mark": sesion.shipping_mark,
        "foto": None,
        "referencia": item.referencia,
        "codigo": item.item_no,
        "desc_es": item.descripcion_es,
        "desc_en": item.descripcion_en,
        "desc_zh": item.descripcion_zh,
        "material": item.material,
        "uso": item.uso,
        "cajas": item.ctns,
        "uds_caja": item.qty_por_ctn,
        "unidad": UNIDAD,
        "cant_total": calc["t_qty"],
        "precio_rmb": item.price_rmb,
        "total_rmb": calc["total_rmb"],
        "precio_usd": calc["price_usd"],
        "total_usd": calc["total_usd"],
        "largo": item.largo_cm or None,
        "ancho": item.ancho_cm or None,
        "alto": item.alto_cm or None,
        "cbm": calc["cbm"],
        "t_cbm": calc["t_cbm"],
        "peso": item.gw or None,
        "peso_total": round((item.gw or 0) * (item.ctns or 0), 2) or None,
        "mqt": item.moq_cajas,
        "marca": item.marca,
        "tamano": item.tamano,
        "empaque": item.empaque,
        "etiqueta": item.etiqueta,
        "herrajes": item.herrajes,
        "riata": item.riata,
        "minimo_cajas_tienda": item.minimo_cajas_tienda,
        "minimo_piezas_caja_tienda": item.minimo_piezas_caja_tienda,
    }


_LOGO: bytes | None = None


def _logo_bytes() -> bytes | None:
    """El logo de YUDA para los documentos. Se lee del disco una sola vez."""
    global _LOGO
    if _LOGO is None:
        try:
            _LOGO = (Path(__file__).resolve().parent.parent / "assets" / "logoyuda.png").read_bytes()
        except Exception:
            logger.warning("No se encontro el logo para los documentos")
            _LOGO = b""
    return _LOGO or None


def _labels(idioma: str) -> dict:
    return LABELS.get(idioma, LABELS["es"])


def _descripcion(item, idioma: str) -> str:
    if idioma == "en":
        return item.descripcion_en or item.descripcion_es or ""
    if idioma == "zh":
        return item.descripcion_zh or item.descripcion_es or ""
    return item.descripcion_es or ""


def _numero_cotizacion(sesion: Sesion, fecha: datetime) -> str:
    return f"YUDA-{fecha.strftime('%Y%m%d')}-{sesion.id[:6].upper()}"


def _calcular(item, tipo_cambio: float) -> dict:
    t_qty = (item.qty_por_ctn or 0) * (item.ctns or 0)
    total_rmb = (item.price_rmb or 0) * t_qty
    price_usd = round((item.price_rmb or 0) / tipo_cambio, 4) if tipo_cambio else 0.0
    total_usd = round(price_usd * t_qty, 2)
    # CBM directo de etiqueta si existe; si no, se calcula por dimensiones.
    cbm = round(item.cbm, 6) if getattr(item, "cbm", None) else round(
        (item.largo_cm or 0) * (item.ancho_cm or 0) * (item.alto_cm or 0) / 1_000_000, 6
    )
    t_cbm = round(cbm * (item.ctns or 0), 6)
    return {
        "t_qty": t_qty,
        "total_rmb": round(total_rmb, 2),
        "price_usd": price_usd,
        "total_usd": total_usd,
        "cbm": cbm,
        "t_cbm": t_cbm,
    }


def _descargar_imagen(url: str):
    """Descarga una imagen y la normaliza a JPEG. Devuelve BytesIO o None si falla."""
    try:
        resp = httpx.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        from PIL import Image as PILImage

        pil = PILImage.open(BytesIO(resp.content)).convert("RGB")
        buf = BytesIO()
        # JPEG: son fotos, en PNG el Excel de la cotización pesa varias veces más.
        pil.save(buf, format="JPEG", quality=CALIDAD_JPEG, optimize=True)
        buf.seek(0)
        return buf
    except Exception:
        return None


def _fotos_extra_ordenadas(item) -> list[str]:
    """URLs de las fotos extra de un ítem (más ángulos, o detalle de bolso),
    en orden estable. El recorte a mano si existe; si no, la original."""
    originales = getattr(item, "fotos_extra", None) or {}
    finales = getattr(item, "fotos_extra_final", None) or {}
    claves = sorted(set(originales) | set(finales))
    urls = [finales.get(k) or originales.get(k) for k in claves]
    return [u for u in urls if u]


def _anclar_imagen(ws, buf, col_idx0: int, row_idx0: int, x_off_px: float, y_off_px: float, lado_px: float) -> None:
    """Coloca una imagen en un punto exacto DENTRO de una celda (columna y
    fila, más un desplazamiento en píxeles), en vez de que openpyxl la
    alinee sola a la esquina de la celda. Así la foto principal y las fotos
    extra de un producto caben juntas en la misma columna "Foto", sin
    agregar columnas nuevas al final."""
    img = XLImage(buf)
    escala = lado_px / max(img.width, img.height)
    img.width = round(img.width * escala)
    img.height = round(img.height * escala)
    marcador = AnchorMarker(
        col=col_idx0, colOff=pixels_to_EMU(x_off_px),
        row=row_idx0, rowOff=pixels_to_EMU(y_off_px),
    )
    tamano = XDRPositiveSize2D(pixels_to_EMU(img.width), pixels_to_EMU(img.height))
    img.anchor = OneCellAnchor(_from=marcador, ext=tamano)
    ws.add_image(img)


def generar_cotizacion_excel(
    items: list, sesion: Sesion, idioma: str, tipo_cambio: float, columnas: list[str] | None = None,
) -> bytes:
    """Genera el Excel de la cotización para el cliente.

    `columnas`: claves de CLAVES_COLUMNAS (+ CLAVES_COLUMNAS_BOLSOS si la
    sesión es de bolsos) a mostrar, elegidas por la vendedora antes de
    descargar; None muestra todas las que apliquen. Foto y Referencia salen
    siempre.
    """
    lab = _labels(idioma)
    etiquetas = ETIQUETAS_COLUMNA[idioma if idioma in ETIQUETAS_COLUMNA else "es"]
    columnas_activas = _columnas_activas(columnas, sesion.tipo_cotizacion == "bolsos")
    fecha = datetime.now()
    wb = Workbook()
    ws = wb.active
    ws.title = "Cotización"

    fill_head = PatternFill(start_color="4B52E8", end_color="4B52E8", fill_type="solid")
    font_head = Font(color="FFFFFF", bold=True)
    fill_alt = PatternFill(start_color="F5F5F0", end_color="F5F5F0", fill_type="solid")
    fill_tot = PatternFill(start_color="0D0D0D", end_color="0D0D0D", fill_type="solid")
    font_tot = Font(color="FFFFFF", bold=True)
    centro = Alignment(horizontal="center", vertical="center")
    lado_borde = Side(style="thin", color="BFBFBF")
    borde_fino = Border(left=lado_borde, right=lado_borde, top=lado_borde, bottom=lado_borde)

    ncols = len(columnas_activas)
    ultima_col = get_column_letter(ncols)

    # Una celda fusionada A1:ultima_col con color de fondo, cuando el
    # documento imprime en más de 1 hoja de ancho, queda con la caja mal
    # calculada en la hoja 1 (se ve un margen absurdo a la derecha) -esto
    # solo les pasa a las celdas fusionadas, no a las individuales. Para las
    # filas con color de fondo (empresa, resumen), se fusiona el texto solo
    # hasta donde cabe la primera hoja, y el resto de columnas se pintan del
    # mismo color SIN fusionar: en pantalla se ve una banda continua, y al
    # imprimir cada celda respeta la página que le toca.
    ANCHO_UTIL_UNA_HOJA = 150  # unidades de ancho de Excel (~27.7cm útiles a 1cm de margen, A4 horizontal)
    acumulado = 0
    col_banner_idx = ncols
    for i, clave in enumerate(columnas_activas, start=1):
        acumulado += ANCHOS_COLUMNA[clave]
        if acumulado > ANCHO_UTIL_UNA_HOJA:
            col_banner_idx = max(1, i - 1)
            break
    col_banner = get_column_letter(col_banner_idx)

    def _fila_banner(fila_banner: int, fill: PatternFill) -> None:
        for col in range(col_banner_idx + 1, ncols + 1):
            ws.cell(row=fila_banner, column=col).fill = fill

    # Logo de YUDA, sobre fondo blanco: el lockup tiene el texto en negro y no se
    # lee sobre el azul del encabezado.
    ws.merge_cells(f"A1:{ultima_col}1")
    ws.row_dimensions[1].height = 58
    logo = _logo_bytes()
    if logo is not None:
        try:
            img_logo = XLImage(BytesIO(logo))
            escala = 64 / img_logo.height
            img_logo.width = round(img_logo.width * escala)
            img_logo.height = 64
            ws.add_image(img_logo, "A1")
        except Exception:
            ws["A1"] = lab["empresa"]

    # Ya no va la banda azul oscuro de "YUDA IMPORTACIONES" (filas 2 y 3):
    # ocupaba espacio y, al imprimir en 2 hojas, el texto salía cortado a la
    # mitad en la segunda ("YUDA IMPORTACIO..."). El logo de la fila 1 ya
    # identifica la empresa; estas filas quedan ocultas para recuperar el
    # espacio en vez de renumerar todo lo que sigue.
    ws.row_dimensions[2].height = 0
    ws.row_dimensions[3].height = 0

    # Aviso de la agencia de carga: sin estos datos no cargan la mercancía
    for i, linea in enumerate(AVISO_AGENCIA):
        f_aviso = 4 + i
        ws.merge_cells(f"A{f_aviso}:{ultima_col}{f_aviso}")
        celda = ws.cell(row=f_aviso, column=1, value=linea)
        celda.font = Font(color="C00000", bold=True, size=9)
        celda.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.row_dimensions[f_aviso].height = 28

    # Datos de la cotización
    numero = _numero_cotizacion(sesion, fecha)
    ws["A7"] = f"{lab['numero']}: {numero}"
    ws["A8"] = f"{lab['emision']}: {fecha.strftime('%Y-%m-%d')}"
    ws["A9"] = f"{lab['cliente']}: {sesion.nombre_cliente}"

    # Headers de columnas. Con columnas angostas (números), el título es más
    # largo que el ancho de la columna ("Fecha de recibo", "Cantidad total"):
    # sin wrap_text, ese texto se sale de la celda y se monta sobre el
    # encabezado de al lado, ilegible. Envuelto en 2 líneas cabe siempre.
    fila_head = 12
    alineacion_head = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[fila_head].height = 30
    for idx, clave in enumerate(columnas_activas, start=1):
        celda = ws.cell(row=fila_head, column=idx, value=etiquetas[clave])
        celda.fill = fill_head
        celda.font = font_head
        celda.alignment = alineacion_head
        celda.border = borde_fino

    # Columna de la foto: se resuelve una vez (siempre está en columnas_activas).
    col_foto_idx0 = columnas_activas.index("foto")
    col_foto = get_column_letter(col_foto_idx0 + 1)

    # Filas de datos
    fila = fila_head + 1
    tot_cajas = tot_rmb = tot_usd = tot_cbm = tot_gw = 0.0
    for n, item in enumerate(items, start=1):
        calc = _calcular(item, tipo_cambio)
        valores = _valores_fila(n, item, calc, sesion)
        for idx, clave in enumerate(columnas_activas, start=1):
            celda = ws.cell(row=fila, column=idx, value=valores[clave])
            celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            celda.border = borde_fino
            if n % 2 == 0:
                celda.fill = fill_alt
        # Cuadrícula de 2 columnas (no una sola fila larga): puestas todas en
        # fila, la columna "Foto" se volvía tan ancha que apretaba a todas
        # las demás columnas de la tabla. En cuadrícula la columna se queda
        # angosta y lo que crece es el alto de la fila, que no molesta a nadie.
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        urls_extra = _fotos_extra_ordenadas(item)[:4]
        urls_fotos_fila = ([foto_doc] if foto_doc else []) + urls_extra
        filas_foto = max(1, -(-len(urls_fotos_fila) // 2))  # redondeo hacia arriba
        ws.row_dimensions[fila].height = filas_foto * (LADO_FOTO_CLIENTE + GAP_FOTO_CLIENTE) * 0.75 + 4

        for i, url_foto in enumerate(urls_fotos_fila):
            buf_foto = _descargar_imagen(url_foto)
            if buf_foto is None:
                continue
            col_foto, fila_foto = i % 2, i // 2
            try:
                _anclar_imagen(
                    ws, buf_foto, col_foto_idx0, fila - 1,
                    x_off_px=6 + col_foto * (LADO_FOTO_CLIENTE + GAP_FOTO_CLIENTE),
                    y_off_px=4 + fila_foto * (LADO_FOTO_CLIENTE + GAP_FOTO_CLIENTE),
                    lado_px=LADO_FOTO_CLIENTE,
                )
            except Exception:
                pass

        tot_cajas += item.ctns or 0
        tot_rmb += calc["total_rmb"]
        tot_usd += calc["total_usd"]
        tot_cbm += calc["t_cbm"]
        tot_gw += round((item.gw or 0) * (item.ctns or 0), 2)
        fila += 1

    # Fila de totales: "TOTALES" en la primera columna, cada total en la suya
    # (si esa columna está oculta, ese total simplemente no sale).
    totales_por_clave = {
        "cajas": int(tot_cajas),
        "total_rmb": round(tot_rmb, 2),
        "total_usd": round(tot_usd, 2),
        "t_cbm": round(tot_cbm, 6),
        "peso_total": round(tot_gw, 2),
    }
    ws.cell(row=fila, column=1, value=lab["totales"])
    for idx, clave in enumerate(columnas_activas, start=1):
        if clave in totales_por_clave:
            ws.cell(row=fila, column=idx, value=totales_por_clave[clave])

    # Recuadro de resumen amigable, arriba de la tabla
    fill_resumen = PatternFill(start_color="EEF0FD", end_color="EEF0FD", fill_type="solid")
    ws.merge_cells(f"A11:{col_banner}11")
    ws["A11"] = lab["resumen"].format(
        n=len(items),
        cajas=int(tot_cajas),
        usd=round(tot_usd, 2),
        gw=round(tot_gw, 2),
        cbm=round(tot_cbm, 6),
    )
    ws["A11"].fill = fill_resumen
    ws["A11"].font = Font(bold=True, color="4B52E8", size=11)
    ws["A11"].alignment = centro
    ws.row_dimensions[11].height = 24
    _fila_banner(11, fill_resumen)
    for col in range(1, ncols + 1):
        c = ws.cell(row=fila, column=col)
        c.fill = fill_tot
        c.font = font_tot
        c.border = borde_fino

    # Nota
    fila_nota = fila + 2
    ws.merge_cells(f"A{fila_nota}:{ultima_col}{fila_nota}")
    ws.cell(row=fila_nota, column=1, value=lab["nota"])

    # Contacto completo
    fila_contacto = fila_nota + 2
    contacto_lineas = [
        f"{CONTACTO['dir_china']}",
        f"{CONTACTO['dir_colombia']}",
        f"{CONTACTO['email']} · {CONTACTO['telefono']} · {CONTACTO['web']}",
    ]
    for i, linea in enumerate(contacto_lineas):
        ws.merge_cells(f"A{fila_contacto + i}:{ultima_col}{fila_contacto + i}")
        ws.cell(row=fila_contacto + i, column=1, value=linea)

    # Anchos de columna
    for idx, clave in enumerate(columnas_activas, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ANCHOS_COLUMNA[clave]

    # Configuración de impresión: horizontal, en 2 hojas de ancho (fitToWidth=1
    # cabía todo pero con ~30 columnas de bolsos el texto quedaba ilegible: hay
    # que elegir entre legible-en-2-hojas o diminuto-en-1-hoja, y "no se puede
    # leer" es peor que "hay que pegar 2 hojas"). fitToHeight=0 deja que las
    # filas caigan a más hojas hacia abajo si hay muchos productos, pero nunca
    # corta columnas a los lados. Numero/Fecha/Marca/Foto/Referencia/Código se
    # repiten en cada hoja de ancho para poder identificar la fila.
    fila_final = fila_contacto + len(contacto_lineas) - 1
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 2
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_area = f"A1:{ultima_col}{fila_final}"
    ws.print_options.horizontalCentered = True
    ws.print_title_cols = f"A:{get_column_letter(min(6, ncols))}"
    # Márgenes al mínimo real que deja imprimir una impresora normal (0.5cm):
    # sin esto Excel usa sus márgenes por defecto (~1.8cm), que sobre una hoja
    # ya apretada de columnas es espacio desperdiciado. Sin encabezado/pie de
    # página: no se usan, no hace falta dejarles espacio.
    margen_medio_cm = 0.5 / 2.54
    ws.page_margins = PageMargins(
        left=margen_medio_cm, right=margen_medio_cm, top=margen_medio_cm, bottom=margen_medio_cm,
        header=0, footer=0,
    )

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generar_cotizacion_pdf(
    items: list, sesion: Sesion, idioma: str, tipo_cambio: float, columnas: list[str] | None = None,
) -> bytes:
    """Genera el PDF de la cotización para el cliente con WeasyPrint.

    `columnas`: ver generar_cotizacion_excel.
    """
    lab = _labels(idioma)
    etiquetas = ETIQUETAS_COLUMNA[idioma if idioma in ETIQUETAS_COLUMNA else "es"]
    columnas_activas = _columnas_activas(columnas, sesion.tipo_cotizacion == "bolsos")
    fecha = datetime.now()
    numero = _numero_cotizacion(sesion, fecha)

    filas_html = []
    tot_cajas = tot_rmb = tot_usd = tot_cbm = tot_gw = 0.0
    for n, item in enumerate(items, start=1):
        calc = _calcular(item, tipo_cambio)
        gw_total = round((item.gw or 0) * (item.ctns or 0), 2)
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        foto_principal = f'<img src="{foto_doc}" />' if foto_doc else ""
        # Fotos extra (más ángulos que pidió el cliente, o detalle del bolso):
        # AL LADO de la principal y del mismo tamaño -no minúsculas debajo-,
        # en la MISMA celda de la columna "Foto" (no columnas nuevas al final).
        urls_extra = _fotos_extra_ordenadas(item)[:4]
        extra_html = "".join(f'<img src="{u}" />' for u in urls_extra)
        foto = f'<div class="fotos-fila">{foto_principal}{extra_html}</div>'
        alt = ' class="alt"' if n % 2 == 0 else ""
        celdas_por_clave = {
            "numero": f"<td>{n}</td>",
            "fecha_recibo": f"<td>{item.fecha_recibo or ''}</td>",
            "shipping_mark": f"<td>{sesion.shipping_mark or ''}</td>",
            "foto": f'<td class="foto">{foto}</td>',
            "referencia": f"<td>{item.referencia or ''}</td>",
            "codigo": f"<td>{item.item_no or ''}</td>",
            "desc_es": f'<td class="desc">{item.descripcion_es or ""}</td>',
            "desc_en": f'<td class="desc">{item.descripcion_en or ""}</td>',
            "desc_zh": f'<td class="desc">{item.descripcion_zh or ""}</td>',
            "material": f"<td>{item.material or ''}</td>",
            "uso": f"<td>{item.uso or ''}</td>",
            "cajas": f"<td>{item.ctns or 0}</td>",
            "uds_caja": f"<td>{item.qty_por_ctn or 0}</td>",
            "unidad": f"<td>{UNIDAD}</td>",
            "cant_total": f"<td>{calc['t_qty']}</td>",
            "precio_rmb": f"<td>{item.price_rmb or 0}</td>",
            "total_rmb": f"<td>{calc['total_rmb']}</td>",
            "precio_usd": f"<td>{calc['price_usd']}</td>",
            "total_usd": f"<td>{calc['total_usd']}</td>",
            "largo": f"<td>{item.largo_cm or ''}</td>",
            "ancho": f"<td>{item.ancho_cm or ''}</td>",
            "alto": f"<td>{item.alto_cm or ''}</td>",
            "cbm": f"<td>{calc['cbm']}</td>",
            "t_cbm": f"<td>{calc['t_cbm']}</td>",
            "peso": f"<td>{item.gw or ''}</td>",
            "peso_total": f"<td>{gw_total or ''}</td>",
            "mqt": f"<td>{item.moq_cajas if item.moq_cajas is not None else ''}</td>",
            "marca": f"<td>{item.marca or ''}</td>",
            "tamano": f"<td>{item.tamano or ''}</td>",
            "empaque": f"<td>{item.empaque or ''}</td>",
            "etiqueta": f"<td>{item.etiqueta or ''}</td>",
            "herrajes": f"<td>{item.herrajes or ''}</td>",
            "riata": f"<td>{item.riata or ''}</td>",
            "minimo_cajas_tienda": f"<td>{item.minimo_cajas_tienda if item.minimo_cajas_tienda is not None else ''}</td>",
            "minimo_piezas_caja_tienda": (
                f"<td>{item.minimo_piezas_caja_tienda if item.minimo_piezas_caja_tienda is not None else ''}</td>"
            ),
        }
        filas_html.append(
            f"<tr{alt}>" + "".join(celdas_por_clave[c] for c in columnas_activas) + "</tr>"
        )
        tot_cajas += item.ctns or 0
        tot_rmb += calc["total_rmb"]
        tot_usd += calc["total_usd"]
        tot_cbm += calc["t_cbm"]
        tot_gw += gw_total

    headers_html = "".join(f"<th>{etiquetas[c]}</th>" for c in columnas_activas)

    logo = _logo_bytes()
    logo_html = (
        f'<div class="logo"><img src="data:image/png;base64,'
        f'{base64.b64encode(logo).decode()}" /></div>'
        if logo
        else ""
    )
    aviso_html = "".join(f"<p>{linea}</p>" for linea in AVISO_AGENCIA)
    nota = lab["nota"]

    # "TOTALES" va en la primera columna activa; cada total, en la suya (si
    # esa columna está oculta, ese total simplemente no sale).
    totales_por_clave = {
        "cajas": int(tot_cajas),
        "total_rmb": round(tot_rmb, 2),
        "total_usd": round(tot_usd, 2),
        "t_cbm": round(tot_cbm, 6),
        "peso_total": round(tot_gw, 2),
    }
    celdas_totales_html = "".join(
        f"<td>{lab['totales']}</td>" if i == 0 else f"<td>{totales_por_clave.get(clave, '')}</td>"
        for i, clave in enumerate(columnas_activas)
    )

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  /* Vuelve a A3: en A4, una cotización de bolsos con todas las columnas
     activadas no entraba -las últimas (precios, totales, tamaño, empaque,
     etc.) quedaban directamente fuera de la página, no solo apretadas. Eso
     es perder datos del documento, mucho peor que el problema original de
     A3 (que un cliente sin esa impresora la reescala sola al imprimir). */
  @page {{ size: A3 landscape; margin: 1cm; }}
  * {{ font-family: Arial, "Noto Sans CJK SC", sans-serif; }}
  body {{ color: #0D0D0D; font-size: 8px; }}
  .empresa {{ background: #1E3A5F; color: #fff; padding: 12px; text-align: center; }}
  .empresa h1 {{ margin: 0; font-size: 18px; }}
  .empresa p {{ margin: 2px 0 0; font-size: 10px; }}
  .datos {{ margin: 10px 0; font-size: 10px; }}
  .datos div {{ margin: 2px 0; }}
  /* table-layout: fixed se probó para esto y resultó peor: si el ancho de
     las columnas suma más que la página, weasyprint no las reescala, las
     CORTA -columnas enteras (precios, totales, tamaño, etc.) desaparecían
     del documento en cotizaciones con muchas columnas (bolsos). Se vuelve a
     ancho automático: la tabla puede pasarse un poco del margen derecho en
     casos extremos, pero nunca pierde datos, que es peor. */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #4B52E8; color: #fff; padding: 4px; font-size: 8px; }}
  /* overflow-wrap: sin esto, una sola palabra larga (una marca, "desmontable",
     etc.) le pone un piso de ancho a toda su columna -tenía que caber esa
     palabra entera en una sola línea. Sumado en ~30 columnas, eso solo ya
     superaba el ancho de la página. Dejar que corte la palabra si hace falta
     es la diferencia entre que quepan todas las columnas o no. */
  td {{ border: 1px solid #E5E7EB; padding: 3px; text-align: center; overflow-wrap: break-word; }}
  /* Sin un mínimo, con tantas columnas (más aún en bolsos) el navegador les
     daba el mismo espacio que a una columna corta como "CBM", y el texto
     quedaba partido en una palabra por línea. Las columnas numéricas cortas
     sí pueden achicarse para compensar, un número no se lee peor angosto. */
  td.desc {{ text-align: left; min-width: 80px; }}
  .logo {{ text-align: center; padding: 6px 0; }}
  .logo img {{ height: 50px; }}
  .aviso {{ border: 1px solid #C00000; color: #C00000; font-weight: bold; font-size: 8px;
            padding: 6px 8px; margin: 8px 0; line-height: 1.35; }}
  .aviso p {{ margin: 0 0 3px; }}
  tr.alt td {{ background: #F5F5F0; }}
  /* La principal y las de detalle van en fila, del mismo tamaño: antes las
     de detalle salían diminutas (20px) y con object-fit: cover, que las
     recortaba otra vez para llenar ese cuadrito -encima de cualquier
     recorte a mano que ya se les hubiera hecho. */
  /* Cuadrícula de 2 columnas, no una sola fila larga: puestas todas en fila,
     la columna se volvía tan ancha que apretaba a las demás columnas de la
     tabla. En cuadrícula la columna se queda angosta y crece el alto de la
     fila en su lugar, que no molesta a nadie. */
  /* overflow: hidden como red de seguridad: CSS grid dentro de una celda de
     tabla se pasaba de ancho en algunos casos y las fotos quedaban ENCIMA de
     las columnas siguientes (Referencia, Código), en vez de forzar el ancho
     de la celda. inline-block con ancho fijo por foto es más simple y
     confiable -se acomodan solas de a 2 por fila, como el texto. */
  td.foto {{ width: 150px; overflow: hidden; }}
  td.foto .fotos-fila {{ width: 138px; }}
  td.foto .fotos-fila img {{
    width: 65px; height: 65px; object-fit: contain; display: inline-block;
    vertical-align: top; margin: 2px;
  }}
  tr.totales td {{ background: #0D0D0D; color: #fff; font-weight: bold; }}
  .resumen {{ background: #EEF0FD; color: #4B52E8; font-weight: bold; text-align: center;
             padding: 8px; border-radius: 8px; margin: 8px 0; font-size: 11px; }}
  .nota {{ margin: 12px 0; font-size: 9px; font-style: italic; }}
  .contacto {{ margin-top: 10px; font-size: 8px; color: #6B7280; border-top: 1px solid #E5E7EB; padding-top: 6px; }}
</style></head><body>
  {logo_html}
  <div class="empresa">
    <h1>{lab['empresa']}</h1>
    <p>{CONTACTO['razon']}</p>
  </div>
  <div class="aviso">{aviso_html}</div>
  <div class="datos">
    <div><strong>{lab['numero']}:</strong> {numero}</div>
    <div><strong>{lab['emision']}:</strong> {fecha.strftime('%Y-%m-%d')}</div>
    <div><strong>{lab['cliente']}:</strong> {sesion.nombre_cliente}</div>
  </div>
  <div class="resumen">{lab['resumen'].format(n=len(items), cajas=int(tot_cajas), usd=round(tot_usd, 2), gw=round(tot_gw, 2), cbm=round(tot_cbm, 6))}</div>
  <table>
    <thead><tr>{headers_html}</tr></thead>
    <tbody>
      {''.join(filas_html)}
      <tr class="totales">{celdas_totales_html}</tr>
    </tbody>
  </table>
  <p class="nota">{nota}</p>
  <div class="contacto">
    {CONTACTO['dir_china']}<br/>
    {CONTACTO['dir_colombia']}<br/>
    {CONTACTO['email']} · {CONTACTO['telefono']} · {CONTACTO['web']}
  </div>
</body></html>"""

    return render_pdf(html)
