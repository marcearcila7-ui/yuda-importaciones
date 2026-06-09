import os
from copy import copy
from datetime import date
from io import BytesIO

from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter, range_boundaries

from app.services.imagen_service import descargar_imagen_png

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


def generar_packing_list_excel(
    items: list, sesion_nombre_cliente: str, tipo_cambio_usd: float
) -> bytes:
    """Genera el Excel del Packing List con fórmulas vivas y devuelve sus bytes"""
    wb = Workbook()
    ws = wb.active
    ws.title = "Packing List"

    # Estilos reutilizables
    fill_header = PatternFill(start_color="404040", end_color="404040", fill_type="solid")
    font_header = Font(color="FFFFFF", bold=True)
    fill_ctns = PatternFill(start_color="BDD7EE", end_color="BDD7EE", fill_type="solid")
    font_usd = Font(color="FF0000")
    font_bold = Font(bold=True)
    centro = Alignment(horizontal="center", vertical="center")

    ultima_col = len(ENCABEZADOS)  # 23

    # Fila 1 y 2: encabezado de la empresa, mergeados de A hasta T
    ws.merge_cells("A1:T1")
    ws["A1"] = "义乌市与达贸易有限公司  YIWU YUDA TRADING CO.,LTD"
    ws["A1"].font = font_bold
    ws["A1"].alignment = centro

    ws.merge_cells("A2:T2")
    ws["A2"] = "义乌市稠州北路1121号福田大厦A座0909-0911室  |  Tel: +86 18058944598"
    ws["A2"].alignment = centro

    # Fila 3: encabezados de columnas
    for idx, titulo in enumerate(ENCABEZADOS, start=1):
        celda = ws.cell(row=3, column=idx, value=titulo)
        celda.fill = fill_header
        celda.font = font_header
        celda.alignment = centro

    # Filas de datos desde la fila 4
    fila = 4
    for item in items:
        ws.cell(row=fila, column=1, value=getattr(item, "supplier_nombre", None))
        # Columna 2 (PHOTO): descargar la foto e incrustarla en la celda
        if getattr(item, "foto_url", None):
            buf = descargar_imagen_png(item.foto_url, lado_px=120)
            if buf is not None:
                try:
                    img = XLImage(buf)
                    img.width = 55
                    img.height = 55
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
    for idx, ancho in enumerate(ANCHOS, start=1):
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


def _descripcion_proveedor(item) -> str:
    """Para el proveedor chino, priorizar la descripción en chino."""
    return (
        getattr(item, "descripcion_zh", None)
        or getattr(item, "descripcion_es", None)
        or getattr(item, "descripcion_en", None)
        or ""
    )


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
    supplier_nombre: str, supplier_numero: str, items: list, fecha: date
) -> bytes:
    """Rellena la plantilla literal FORMATO PEDIDO con los productos del proveedor.

    El sistema completa: NO, foto, ITEM NO, descripción, CTN, QTY/CTN, precio,
    CBM y G.W. Las fórmulas (QTY, AMOUNT, T.CBM, totales) y todo lo demás
    (membrete, fechas, firmas, notas) quedan tal cual el formato original.
    """
    wb = load_workbook(PLANTILLA_PEDIDO)
    ws = wb.active

    n = len(items)
    if n > PED_FILAS_PLANTILLA:
        faltan = n - PED_FILAS_PLANTILLA
        _expandir_pedido(ws, faltan)
        ultima = (PED_FILA0 + n - 1)
        total_row = PED_FILA_TOTALES + faltan
        for col, letra in [(6, "F"), (9, "I"), (11, "K"), (13, "M")]:
            ws.cell(row=total_row, column=col, value=f"=SUM({letra}{PED_FILA0}:{letra}{ultima})")

    for idx, item in enumerate(items):
        f = PED_FILA0 + idx
        ws.cell(row=f, column=1, value=idx + 1)  # A: NO
        # B: PHOTO — la final (limpia) si existe; si no, la de datos como respaldo.
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        if foto_doc:
            buf = descargar_imagen_png(foto_doc, lado_px=180)
            if buf is not None:
                try:
                    img = XLImage(buf)
                    img.width = 150
                    img.height = 140
                    ws.add_image(img, f"B{f}")
                except Exception:
                    pass
        ws.cell(row=f, column=3, value=getattr(item, "item_no", None))   # C: ITEM NO
        ws.cell(row=f, column=4, value=_descripcion_proveedor(item))     # D: DESCRIPTION
        ws.cell(row=f, column=6, value=getattr(item, "ctns", None))      # F: CTN
        ws.cell(row=f, column=7, value=getattr(item, "qty_por_ctn", None))  # G: QTY/CTN
        ws.cell(row=f, column=10, value=getattr(item, "price_rmb", None))   # J: PRICE
        largo = getattr(item, "largo_cm", 0) or 0
        ancho = getattr(item, "ancho_cm", 0) or 0
        alto = getattr(item, "alto_cm", 0) or 0
        ws.cell(row=f, column=12, value=round(largo * ancho * alto / 1_000_000, 6))  # L: CBM
        ws.cell(row=f, column=14, value=getattr(item, "gw", None))       # N: G.W

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
