from datetime import datetime
from io import BytesIO

import httpx
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from weasyprint import HTML

from app.models.sesion import Sesion

# Datos de contacto de YUDA (hardcodeados en el documento)
CONTACTO = {
    "dir_china": "Room 0909-0911, Building A, Futian Building, No.1121, Chouzhou North Road, Yiwu City, China. Zip: 322023",
    "dir_colombia": "Cr 53 cll 45-115 piso 8 Edificio Multivariedades, Centro de Medellín",
    "email": "info@yudaimport.com",
    "telefono": "+57 123 456 78 90",
    "web": "yudaimport.com",
    "razon": "义乌市与达贸易有限公司 · YIWU YUDA TRADING CO.,LTD",
}

# Etiquetas por idioma
LABELS = {
    "es": {
        "empresa": "YUDA IMPORTACIONES",
        "cols": ["N°", "Foto", "Código", "Descripción", "Material", "Uso", "Cajas", "Uds/Caja", "Total Uds", "Precio RMB", "Total RMB", "Precio USD", "Total USD", "CBM", "T.CBM"],
        "numero": "N° Cotización",
        "emision": "Fecha de emisión",
        "cliente": "Cliente",
        "tipoCambio": "Tipo de cambio",
        "totales": "TOTALES",
        "nota": "Los precios están sujetos a confirmación del proveedor. Tipo de cambio: 1 USD = {tc} RMB",
    },
    "en": {
        "empresa": "YIWU YUDA TRADING CO.,LTD",
        "cols": ["N°", "Photo", "Code", "Description", "Material", "Use", "Boxes", "Units/Box", "Total Units", "Price RMB", "Total RMB", "Price USD", "Total USD", "CBM", "T.CBM"],
        "numero": "Quotation No.",
        "emision": "Issue date",
        "cliente": "Client",
        "tipoCambio": "Exchange rate",
        "totales": "TOTALS",
        "nota": "Prices are subject to supplier confirmation. Exchange rate: 1 USD = {tc} RMB",
    },
    "zh": {
        "empresa": "义乌市与达贸易有限公司",
        "cols": ["序号", "图片", "货号", "描述", "材质", "用途", "箱数", "每箱数量", "总数量", "单价(元)", "总价(元)", "单价(USD)", "总价(USD)", "CBM", "总CBM"],
        "numero": "报价单号",
        "emision": "签发日期",
        "cliente": "客户",
        "tipoCambio": "汇率",
        "totales": "合计",
        "nota": "价格以供应商确认为准。汇率：1 USD = {tc} RMB",
    },
}


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
    cbm = round((item.largo_cm or 0) * (item.ancho_cm or 0) * (item.alto_cm or 0) / 1_000_000, 6)
    t_cbm = round(cbm * (item.ctns or 0), 6)
    return {
        "t_qty": t_qty,
        "total_rmb": round(total_rmb, 2),
        "price_usd": price_usd,
        "total_usd": total_usd,
        "cbm": cbm,
        "t_cbm": t_cbm,
    }


def _descargar_imagen_png(url: str):
    """Descarga una imagen y la normaliza a PNG. Devuelve BytesIO o None si falla."""
    try:
        resp = httpx.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        from PIL import Image as PILImage

        pil = PILImage.open(BytesIO(resp.content)).convert("RGB")
        buf = BytesIO()
        pil.save(buf, format="PNG")
        buf.seek(0)
        return buf
    except Exception:
        return None


def generar_cotizacion_excel(items: list, sesion: Sesion, idioma: str, tipo_cambio: float) -> bytes:
    """Genera el Excel de la cotización para el cliente"""
    lab = _labels(idioma)
    fecha = datetime.now()
    wb = Workbook()
    ws = wb.active
    ws.title = "Cotización"

    fill_empresa = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    font_empresa = Font(color="FFFFFF", bold=True, size=14)
    fill_head = PatternFill(start_color="4B52E8", end_color="4B52E8", fill_type="solid")
    font_head = Font(color="FFFFFF", bold=True)
    fill_alt = PatternFill(start_color="F5F5F0", end_color="F5F5F0", fill_type="solid")
    fill_tot = PatternFill(start_color="0D0D0D", end_color="0D0D0D", fill_type="solid")
    font_tot = Font(color="FFFFFF", bold=True)
    centro = Alignment(horizontal="center", vertical="center")

    ncols = len(lab["cols"])  # 15
    ultima_col = get_column_letter(ncols)  # O

    # Encabezado de empresa
    ws.merge_cells(f"A1:{ultima_col}1")
    ws["A1"] = lab["empresa"]
    ws["A1"].fill = fill_empresa
    ws["A1"].font = font_empresa
    ws["A1"].alignment = centro
    ws.merge_cells(f"A2:{ultima_col}2")
    ws["A2"] = CONTACTO["razon"]
    ws["A2"].fill = fill_empresa
    ws["A2"].font = Font(color="FFFFFF")
    ws["A2"].alignment = centro

    # Datos de la cotización
    numero = _numero_cotizacion(sesion, fecha)
    ws["A4"] = f"{lab['numero']}: {numero}"
    ws["A5"] = f"{lab['emision']}: {fecha.strftime('%Y-%m-%d')}"
    ws["A6"] = f"{lab['cliente']}: {sesion.nombre_cliente}"
    ws["A7"] = f"{lab['tipoCambio']}: 1 USD = {tipo_cambio} RMB"

    # Headers de columnas
    fila_head = 9
    for idx, titulo in enumerate(lab["cols"], start=1):
        celda = ws.cell(row=fila_head, column=idx, value=titulo)
        celda.fill = fill_head
        celda.font = font_head
        celda.alignment = centro

    # Filas de datos
    fila = fila_head + 1
    tot_cajas = tot_rmb = tot_usd = tot_cbm = 0.0
    for n, item in enumerate(items, start=1):
        calc = _calcular(item, tipo_cambio)
        valores = [
            n,
            None,  # Foto (se agrega como imagen)
            item.item_no,
            _descripcion(item, idioma),
            item.material,
            item.uso,
            item.ctns,
            item.qty_por_ctn,
            calc["t_qty"],
            item.price_rmb,
            calc["total_rmb"],
            calc["price_usd"],
            calc["total_usd"],
            calc["cbm"],
            calc["t_cbm"],
        ]
        for idx, val in enumerate(valores, start=1):
            celda = ws.cell(row=fila, column=idx, value=val)
            if n % 2 == 0:
                celda.fill = fill_alt
        ws.row_dimensions[fila].height = 45

        # Foto: descargar y agregar como imagen en la celda B
        if getattr(item, "foto_url", None):
            buf = _descargar_imagen_png(item.foto_url)
            if buf is not None:
                try:
                    img = XLImage(buf)
                    img.width = 55
                    img.height = 55
                    ws.add_image(img, f"B{fila}")
                except Exception:
                    pass

        tot_cajas += item.ctns or 0
        tot_rmb += calc["total_rmb"]
        tot_usd += calc["total_usd"]
        tot_cbm += calc["t_cbm"]
        fila += 1

    # Fila de totales
    ws.cell(row=fila, column=1, value=lab["totales"])
    ws.cell(row=fila, column=7, value=int(tot_cajas))
    ws.cell(row=fila, column=11, value=round(tot_rmb, 2))
    ws.cell(row=fila, column=13, value=round(tot_usd, 2))
    ws.cell(row=fila, column=15, value=round(tot_cbm, 6))
    for col in range(1, ncols + 1):
        c = ws.cell(row=fila, column=col)
        c.fill = fill_tot
        c.font = font_tot

    # Nota
    fila_nota = fila + 2
    ws.merge_cells(f"A{fila_nota}:{ultima_col}{fila_nota}")
    ws.cell(row=fila_nota, column=1, value=lab["nota"].format(tc=tipo_cambio))

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
    anchos = [5, 12, 12, 30, 14, 12, 8, 9, 10, 11, 11, 11, 11, 9, 9]
    for idx, ancho in enumerate(anchos, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = ancho

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def generar_cotizacion_pdf(items: list, sesion: Sesion, idioma: str, tipo_cambio: float) -> bytes:
    """Genera el PDF de la cotización para el cliente con WeasyPrint"""
    lab = _labels(idioma)
    fecha = datetime.now()
    numero = _numero_cotizacion(sesion, fecha)

    filas_html = []
    tot_cajas = tot_rmb = tot_usd = tot_cbm = 0.0
    for n, item in enumerate(items, start=1):
        calc = _calcular(item, tipo_cambio)
        foto = (
            f'<img src="{item.foto_url}" />'
            if getattr(item, "foto_url", None)
            else ""
        )
        alt = ' class="alt"' if n % 2 == 0 else ""
        filas_html.append(
            f"<tr{alt}>"
            f"<td>{n}</td>"
            f'<td class="foto">{foto}</td>'
            f"<td>{item.item_no or ''}</td>"
            f"<td>{_descripcion(item, idioma)}</td>"
            f"<td>{item.material or ''}</td>"
            f"<td>{item.uso or ''}</td>"
            f"<td>{item.ctns or 0}</td>"
            f"<td>{item.qty_por_ctn or 0}</td>"
            f"<td>{calc['t_qty']}</td>"
            f"<td>{item.price_rmb or 0}</td>"
            f"<td>{calc['total_rmb']}</td>"
            f"<td>{calc['price_usd']}</td>"
            f"<td>{calc['total_usd']}</td>"
            f"<td>{calc['cbm']}</td>"
            f"<td>{calc['t_cbm']}</td>"
            f"</tr>"
        )
        tot_cajas += item.ctns or 0
        tot_rmb += calc["total_rmb"]
        tot_usd += calc["total_usd"]
        tot_cbm += calc["t_cbm"]

    headers_html = "".join(f"<th>{c}</th>" for c in lab["cols"])
    nota = lab["nota"].format(tc=tipo_cambio)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  @page {{ size: A4 landscape; margin: 1.2cm; }}
  * {{ font-family: Arial, "Noto Sans CJK SC", sans-serif; }}
  body {{ color: #0D0D0D; font-size: 9px; }}
  .empresa {{ background: #1E3A5F; color: #fff; padding: 12px; text-align: center; }}
  .empresa h1 {{ margin: 0; font-size: 18px; }}
  .empresa p {{ margin: 2px 0 0; font-size: 10px; }}
  .datos {{ margin: 10px 0; font-size: 10px; }}
  .datos div {{ margin: 2px 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #4B52E8; color: #fff; padding: 5px; font-size: 9px; }}
  td {{ border: 1px solid #E5E7EB; padding: 4px; text-align: center; }}
  tr.alt td {{ background: #F5F5F0; }}
  td.foto img {{ max-width: 50px; max-height: 50px; }}
  tr.totales td {{ background: #0D0D0D; color: #fff; font-weight: bold; }}
  .nota {{ margin: 12px 0; font-size: 9px; font-style: italic; }}
  .contacto {{ margin-top: 10px; font-size: 8px; color: #6B7280; border-top: 1px solid #E5E7EB; padding-top: 6px; }}
</style></head><body>
  <div class="empresa">
    <h1>{lab['empresa']}</h1>
    <p>{CONTACTO['razon']}</p>
  </div>
  <div class="datos">
    <div><strong>{lab['numero']}:</strong> {numero}</div>
    <div><strong>{lab['emision']}:</strong> {fecha.strftime('%Y-%m-%d')}</div>
    <div><strong>{lab['cliente']}:</strong> {sesion.nombre_cliente}</div>
    <div><strong>{lab['tipoCambio']}:</strong> 1 USD = {tipo_cambio} RMB</div>
  </div>
  <table>
    <thead><tr>{headers_html}</tr></thead>
    <tbody>
      {''.join(filas_html)}
      <tr class="totales">
        <td colspan="6">{lab['totales']}</td>
        <td>{int(tot_cajas)}</td><td></td><td></td><td></td>
        <td>{round(tot_rmb, 2)}</td><td></td><td>{round(tot_usd, 2)}</td>
        <td></td><td>{round(tot_cbm, 6)}</td>
      </tr>
    </tbody>
  </table>
  <p class="nota">{nota}</p>
  <div class="contacto">
    {CONTACTO['dir_china']}<br/>
    {CONTACTO['dir_colombia']}<br/>
    {CONTACTO['email']} · {CONTACTO['telefono']} · {CONTACTO['web']}
  </div>
</body></html>"""

    return HTML(string=html).write_pdf()
