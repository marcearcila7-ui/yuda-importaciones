import os
from copy import copy
from datetime import date
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, range_boundaries

from app.services.imagen_service import descargar_imagen

# Plantilla literal del formato de pedido al proveedor (FORMATO PEDIDO de YUDA)
PLANTILLA_PEDIDO = os.path.join(
    os.path.dirname(__file__), "..", "templates", "formato_pedido.xlsx"
)

# Encabezados en el orden exacto del Packing List (columnas A..W)
ENCABEZADOS = [
    "SUPPLIER", "PHOTO", "ITEM NO", "ESPAÑOL", "ENGLISH", "中文", "MATERIAL",
    "USO", "CTNS", "QTY/CTN", "UNIT", "T.QTY", "PRICE RMB", "TOTAL ¥",
    "PRICE USD", "TOTAL USD", "L cm", "W cm", "H cm", "CBM", "T.CBM", "GW", "T.GW",
]

# Anchos de columna aproximados (en el mismo orden que ENCABEZADOS)
ANCHOS = [20, 12, 12, 25, 25, 20, 15, 12, 8, 10, 8, 10, 12, 12, 12, 12, 8, 8, 8, 10, 10, 8, 8]

# Columnas propias de una cotización de bolsos (sesion.tipo_cotizacion == "bolsos"),
# agregadas al final SOLO en ese caso. Van después de T.GW.
ENCABEZADOS_BOLSOS = [
    "COLORES", "TAMAÑO", "EMPAQUE", "ETIQUETA", "HERRAJES", "RIATA",
    "MÍN. CAJAS (TIENDA)", "MÍN. PZS/CAJA (TIENDA)",
    "FOTO INTERIOR", "FOTO HERRAJES", "FOTO RIATA", "FOTO EXTERIOR",
]
ANCHOS_BOLSOS = [15, 12, 15, 15, 12, 15, 14, 14, 12, 12, 12, 12]

# Fotos de detalle del bolso (item.fotos_extra), en el mismo orden en que se
# agregan las columnas de arriba.
TIPOS_FOTO_EXTRA_EXCEL = ["interior", "herrajes", "riata", "exterior"]


def _encajar(img: XLImage, lado_max: int) -> None:
    """Achica una imagen de openpyxl a que su lado más largo mida `lado_max`,
    respetando la proporción original. Sin esto, fijar width/height por igual
    en una foto que no es cuadrada la deja estirada/aplastada."""
    escala = lado_max / max(img.width, img.height)
    img.width = round(img.width * escala)
    img.height = round(img.height * escala)


def generar_packing_list_excel(
    items: list, sesion_nombre_cliente: str, tipo_cambio_usd: float,
    tipo_cotizacion: str = "productos",
) -> bytes:
    """Genera el Excel del Packing List con fórmulas vivas y devuelve sus bytes.

    En modo bolsos agrega columnas propias (colores, tamaño, empaque, etiqueta,
    herrajes, riata, los dos mínimos de tienda) al final; en productos varios el
    Excel queda exactamente igual que siempre.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Packing List"

    es_bolsos = tipo_cotizacion == "bolsos"
    encabezados = ENCABEZADOS + ENCABEZADOS_BOLSOS if es_bolsos else ENCABEZADOS
    anchos = ANCHOS + ANCHOS_BOLSOS if es_bolsos else ANCHOS

    # Estilos reutilizables
    fill_header = PatternFill(start_color="404040", end_color="404040", fill_type="solid")
    font_header = Font(color="FFFFFF", bold=True)
    fill_ctns = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
    font_usd = Font(color="FF0000")
    font_bold = Font(bold=True)
    centro = Alignment(horizontal="center", vertical="center")

    ultima_col = len(encabezados)  # 23, o 31 en modo bolsos

    # Fila 1 y 2: encabezado de la empresa, mergeados de A hasta T
    ws.merge_cells("A1:T1")
    ws["A1"] = "义乌市与达贸易有限公司  YIWU YUDA TRADING CO.,LTD"
    ws["A1"].font = font_bold
    ws["A1"].alignment = centro

    ws.merge_cells("A2:T2")
    ws["A2"] = "义乌市稠州北路1121号福田大厦A座0909-0911室  |  Tel: +86 18058944598"
    ws["A2"].alignment = centro

    # Fila 3: encabezados de columnas
    for idx, titulo in enumerate(encabezados, start=1):
        celda = ws.cell(row=3, column=idx, value=titulo)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = centro

    # Filas de datos desde la fila 4
    fila = 4
    for item in items:
        ws.cell(row=fila, column=1, value=getattr(item, "supplier_nombre", None))
        # Columna 2 (PHOTO): descargar la foto e incrustarla en la celda.
        # Final (recortada a mano o por el OCR) si existe; si no, la original.
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        if foto_doc:
            buf = descargar_imagen(foto_doc, lado_px=120)
            if buf is not None:
                try:
                    img = XLImage(buf)
                    _encajar(img, 55)
                    ws.add_image(img, f"B{fila}")
                    ws.row_dimensions[fila].height = 45
                except Exception:
                    pass
        ws.cell(row=fila, column=3, value=getattr(item, "item_no", None))
        ws.cell(row=fila, column=4, value=getattr(item, "descripcion_es", None))
        ws.cell(row=fila, column=5, value=getattr(item, "descripcion_en", None))
        ws.cell(row=fila, column=6, value=getattr(item, "descripcion_zh", None))
        ws.cell(row=fila, column=7, value=getattr(item, "material", None))
        ws.cell(row=fila, column=8, value=getattr(item, "uso", None))
        # CTNS (col I) con fondo azul claro
        celda_ctns = ws.cell(row=fila, column=9, value=getattr(item, "ctns", None))
        celda_ctns.fill = fill_ctns
        ws.cell(row=fila, column=10, value=getattr(item, "qty_por_ctn", None))
        ws.cell(row=fila, column=11, value="PCS")
        # T.QTY (col L) = I*J
        ws.cell(row=fila, column=12, value=f"=I{fila}*J{fila}")
        ws.cell(row=fila, column=13, value=getattr(item, "price_rmb", None))
        # TOTAL ¥ (col N) = M*L
        ws.cell(row=fila, column=14, value=f"=M{fila}*L{fila}")
        # PRICE USD (col O) = M/tipo_cambio, texto rojo
        celda_usd = ws.cell(row=fila, column=15, value=f"=M{fila}/{tipo_cambio_usd}")
        celda_usd.font = font_usd
        # TOTAL USD (col P) = O*L
        ws.cell(row=fila, column=16, value=f"=O{fila}*L{fila}")
        ws.cell(row=fila, column=17, value=getattr(item, "largo_cm", None))
        ws.cell(row=fila, column=18, value=getattr(item, "ancho_cm", None))
        ws.cell(row=fila, column=19, value=getattr(item, "alto_cm", None))
        # CBM (col T) = Q*R*S/1000000
        ws.cell(row=fila, column=20, value=f"=Q{fila}*R{fila}*S{fila}/1000000")
        # T.CBM (col U) = T*I
        ws.cell(row=fila, column=21, value=f"=T{fila}*I{fila}")
        ws.cell(row=fila, column=22, value=getattr(item, "gw", None))
        # T.GW (col W) = V*I
        ws.cell(row=fila, column=23, value=f"=V{fila}*I{fila}")
        if es_bolsos:
            ws.cell(row=fila, column=24, value=getattr(item, "colores", None))
            ws.cell(row=fila, column=25, value=getattr(item, "tamano", None))
            ws.cell(row=fila, column=26, value=getattr(item, "empaque", None))
            ws.cell(row=fila, column=27, value=getattr(item, "etiqueta", None))
            ws.cell(row=fila, column=28, value=getattr(item, "herrajes", None))
            ws.cell(row=fila, column=29, value=getattr(item, "riata", None))
            ws.cell(row=fila, column=30, value=getattr(item, "minimo_cajas_tienda", None))
            ws.cell(row=fila, column=31, value=getattr(item, "minimo_piezas_caja_tienda", None))
            # Fotos de detalle (interior/herrajes/riata/exterior), columnas 32..35.
            # El recorte a mano si existe; si no, la original tal como se subió.
            fotos_extra = getattr(item, "fotos_extra", None) or {}
            fotos_extra_final = getattr(item, "fotos_extra_final", None) or {}
            for offset, tipo in enumerate(TIPOS_FOTO_EXTRA_EXCEL):
                url = fotos_extra_final.get(tipo) or fotos_extra.get(tipo)
                if not url:
                    continue
                buf = descargar_imagen(url, lado_px=120)
                if buf is not None:
                    try:
                        img = XLImage(buf)
                        _encajar(img, 55)
                        ws.add_image(img, f"{get_column_letter(32 + offset)}{fila}")
                        ws.row_dimensions[fila].height = 45
                    except Exception:
                        pass
        fila += 1

    ultima_fila_datos = fila - 1 if items else 3
    fila_totales = fila

    # Fila de TOTALES
    celda_tot = ws.cell(row=fila_totales, column=1, value="TOTALES:")
    celda_tot.font = font_bold
    ws.cell(row=fila_totales, column=9, value=f"=SUM(I4:I{ultima_fila_datos})")
    ws.cell(row=fila_totales, column=14, value=f"=SUM(N4:N{ultima_fila_datos})")
    ws.cell(row=fila_totales, column=16, value=f"=SUM(P4:P{ultima_fila_datos})")
    ws.cell(row=fila_totales, column=21, value=f"=SUM(U4:U{ultima_fila_datos})")
    # Toda la fila de totales en negrita
    for col in range(1, ultima_col + 1):
        ws.cell(row=fila_totales, column=col).font = font_bold

    # Anchos de columna
    for idx, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ancho

    # Guardar en memoria y devolver los bytes
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def agrupar_items_por_supplier(items: list) -> dict:
    """Agrupa ítems por proveedor (nombre + número), ordenado por clave alfabética"""
    grupos: dict[str, list] = {}
    for item in items:
        nombre = getattr(item, "supplier_nombre", None) or "Sin_Proveedor"
        numero = getattr(item, "supplier_numero", None) or "SN"
        clave = f"{nombre}_{numero}"
        grupos.setdefault(clave, []).append(item)
    # Devolver ordenado alfabéticamente por clave; el orden interno se conserva
    return {clave: grupos[clave] for clave in sorted(grupos)}


# ─── Formato de pedido al proveedor: se rellena la plantilla LITERAL de YUDA ───

# La plantilla trae 11 filas de productos (7..17) y la fila de totales en la 18.
PED_FILA0 = 7
PED_FILAS_PLANTILLA = 11
PED_FILA_TOTALES = 18

# La foto es LA referencia de lo que se pidió: si algo llega mal, es lo que se le
# muestra al proveedor. Por eso va grande y nítida, y la fila y la columna se
# agrandan para que quepa sin taparle el espacio a ITEM NO (que se rellena a mano).
PED_FOTO_PX = 300  # lado de la imagen dentro de la celda
PED_ALTO_FILA = 232  # puntos (~310 px): la foto entra completa y sobra aire
PED_ANCHO_FOTO = 45  # ancho de la columna B en caracteres (~320 px)
PED_ANCHO_ITEM = 24  # ancho de la columna C (ITEM NO), para escribir a mano


def _descripcion_proveedor(item) -> str:
    """Descripción para el proveedor: SIEMPRE español y chino, uno debajo del otro.

    La vendedora escribe en español y el proveedor lee el chino; con las dos
    juntas nadie tiene que adivinar de qué producto se trata.
    """
    es = getattr(item, "descripcion_es", None) or getattr(item, "descripcion_en", None) or ""
    zh = getattr(item, "descripcion_zh", None) or ""
    return "\n".join([t for t in (es, zh) if t])


def _expandir_pedido(ws, faltan: int) -> None:
    """Agrega 'faltan' filas de producto antes de la fila de totales, clonando
    el estilo y las fórmulas de una fila de datos, y desplazando las celdas
    combinadas y alturas del pie (que openpyxl no mueve solo)."""
    # Guardar y quitar las combinaciones del pie (fila >= totales)
    combinaciones = []
    for m in list(ws.merged_cells.ranges):
        c1, r1, c2, r2 = range_boundaries(str(m))
        if r1 >= PED_FILA_TOTALES:
            combinaciones.append((c1, r1, c2, r2))
            ws.unmerge_cells(str(m))
    alturas = {
        r: ws.row_dimensions[r].height
        for r in list(ws.row_dimensions)
        if r >= PED_FILA_TOTALES and ws.row_dimensions[r].height
    }

    ws.insert_rows(PED_FILA_TOTALES, amount=faltan)

    # Re-aplicar combinaciones y alturas desplazadas
    for c1, r1, c2, r2 in combinaciones:
        ws.merge_cells(start_row=r1 + faltan, start_column=c1, end_row=r2 + faltan, end_column=c2)
    for r, h in alturas.items():
        ws.row_dimensions[r + faltan].height = h

    # Nuevas filas de datos con el estilo y las fórmulas de la fila modelo
    for off in range(faltan):
        nueva = PED_FILA_TOTALES + off
        ws.row_dimensions[nueva].height = ws.row_dimensions[PED_FILA0].height
        for col in range(1, 15):
            ws.cell(row=nueva, column=col)._style = copy(ws.cell(row=PED_FILA0, column=col)._style)
        ws.cell(row=nueva, column=8, value="PCS")
        ws.cell(row=nueva, column=9, value=f"=G{nueva}*F{nueva}")
        ws.cell(row=nueva, column=11, value=f"=J{nueva}*I{nueva}")
        ws.cell(row=nueva, column=13, value=f"=L{nueva}*F{nueva}")


def generar_formato_pedido(
    supplier_nombre: str, supplier_numero: str, items: list, fecha: date,
    fotos: dict | None = None, shipping_mark: str | None = None,
) -> bytes:
    """Rellena la plantilla literal FORMATO PEDIDO con los productos del proveedor.

    El sistema completa: NO, foto, ITEM NO, descripción, CTN, QTY/CTN, precio,
    CBM y G.W. Las fórmulas (QTY, AMOUNT, T.CBM, totales) y todo lo demás
    (membrete, fechas, firmas, notas) quedan tal cual el formato original,
    salvo la marca de embarque (ver más abajo).

    `fotos` mapea url→bytes PNG ya descargados (para no bajar la misma foto dos
    veces ni de forma secuencial). Si falta, cae a descargar la foto en el momento.

    `shipping_mark`: iniciales con las que el proveedor marca las cajas de este
    cliente en su bodega (p. ej. "KAES"), para no confundirlas con las de otro
    pedido. En el formato de papel va dentro de un rombo dibujado a mano; acá se
    escribe en la misma zona (entre "两张正唛" y "两张侧唛"), como texto grande y
    con caja: openpyxl no dibuja formas nuevas con facilidad, pero el rombo en sí
    es decorativo, lo que de verdad tiene que verse es la marca.
    """
    from io import BytesIO
    fotos = fotos or {}
    wb = load_workbook(PLANTILLA_PEDIDO)
    ws = wb.active

    n = len(items)
    faltan = 0
    if n > PED_FILAS_PLANTILLA:
        faltan = n - PED_FILAS_PLANTILLA
        _expandir_pedido(ws, faltan)
        ultima = (PED_FILA0 + n - 1)
        total_row = PED_FILA_TOTALES + faltan
        for col, letra in [(6, "F"), (9, "I"), (11, "K"), (13, "M")]:
            ws.cell(row=total_row, column=col, value=f"=SUM({letra}{PED_FILA0}:{letra}{ultima})")

    # Columnas de la foto y del ITEM NO: la foto va grande y el ITEM NO necesita
    # ancho propio para que se pueda escribir a mano sin que la tape la imagen.
    ws.column_dimensions["B"].width = PED_ANCHO_FOTO
    ws.column_dimensions["C"].width = PED_ANCHO_ITEM

    for idx, item in enumerate(items):
        f = PED_FILA0 + idx
        ws.row_dimensions[f].height = PED_ALTO_FILA
        ws.cell(row=f, column=1, value=idx + 1)  # A: NO
        # B: PHOTO — la final (limpia) si existe; si no, la de datos como respaldo.
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        if foto_doc:
            # Imagen ya descargada (bytes) si está en cache; si no, se baja al momento.
            cache = fotos.get(foto_doc)
            buf = (
                BytesIO(cache) if cache is not None
                else descargar_imagen(foto_doc, lado_px=PED_FOTO_PX * 3)
            )
            if buf is not None:
                try:
                    img = XLImage(buf)
                    # Se respeta la proporción de la foto: nada de estirarla.
                    escala = PED_FOTO_PX / max(img.width, img.height)
                    img.width = round(img.width * escala)
                    img.height = round(img.height * escala)
                    ws.add_image(img, f"B{f}")
                except Exception:
                    pass
        # C: ITEM NO — lo rellenan a mano; queda centrado y con salto de línea.
        celda_item = ws.cell(row=f, column=3, value=getattr(item, "item_no", None))
        celda_item.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        # D: DESCRIPTION (español + chino, una debajo de la otra)
        celda_desc = ws.cell(row=f, column=4, value=_descripcion_proveedor(item))
        celda_desc.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        ws.cell(row=f, column=6, value=getattr(item, "ctns", None))      # F: CTN
        ws.cell(row=f, column=7, value=getattr(item, "qty_por_ctn", None))  # G: QTY/CTN
        ws.cell(row=f, column=10, value=getattr(item, "price_rmb", None))   # J: PRICE
        largo = getattr(item, "largo_cm", 0) or 0
        ancho = getattr(item, "ancho_cm", 0) or 0
        alto = getattr(item, "alto_cm", 0) or 0
        # CBM y peso: si no están cargados, la celda va vacía (un 0 lo lee el
        # proveedor como un dato real equivocado).
        ws.cell(row=f, column=12, value=round(largo * ancho * alto / 1_000_000, 6) or None)  # L: CBM
        ws.cell(row=f, column=14, value=getattr(item, "gw", None) or None)  # N: G.W

    if shipping_mark:
        # Fila de "两张正唛" / "两张侧唛" (2 filas debajo de los totales), columna
        # del medio (L), corrida hacia abajo si el pedido se expandió.
        fila_marca = PED_FILA_TOTALES + 2 + faltan
        celda_marca = ws.cell(row=fila_marca, column=12, value=shipping_mark.strip().upper())
        celda_marca.font = Font(bold=True, size=16)
        celda_marca.alignment = Alignment(horizontal="center", vertical="center")
        borde = Side(style="medium")
        celda_marca.border = Border(top=borde, bottom=borde, left=borde, right=borde)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
