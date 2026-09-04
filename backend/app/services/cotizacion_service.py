import base64
import logging
from datetime import datetime
from io import BytesIO
from pathlib import Path

import httpx
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from app.services.imagen_service import CALIDAD_JPEG
from app.services.pdf_service import render_pdf

from app.models.sesion import Sesion

logger = logging.getLogger(__name__)

# Datos de contacto de YUDA (hardcodeados en el documento)
CONTACTO = {
    "dir_china": "Room 0909-0911, Building A, Futian Building, No.1121, Chouzhou North Road, Yiwu City, China. Zip: 322023",
    "dir_colombia": "Cr 53 cll 45-115 piso 8 Edificio Multivariedades, Centro de Medellín",
    "email": "info@yudaimport.com",
    "telefono": "+57 123 456 78 90",
    "web": "yudaimport.com",
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
        "cols": [
            "N°",
            "Fecha de recibo",
            "Shipping mark",
            "Foto",
            "Referencia",
            "Código",
            "Descripción (Español)",
            "Description (English)",
            "描述 (中文)",
            "Material",
            "Uso",
            "Cajas",
            "Uds/Caja",
            "Unidad",
            "Cantidad total",
            "Precio RMB",
            "Total RMB",
            "Precio USD",
            "Total USD",
            "Largo cm",
            "Ancho cm",
            "Alto cm",
            "CBM",
            "T.CBM",
            "Peso kg",
            "Peso total kg",
            "MQT (mín. cajas)",
            "Marca",
        ],
        "numero": "N° Cotización",
        "emision": "Fecha de emisión",
        "cliente": "Cliente",
        "totales": "TOTALES",
        "nota": "Los precios están sujetos a confirmación del proveedor.",
        "resumen": "RESUMEN:   {n} productos   ·   {cajas} cajas   ·   Total USD ${usd}   ·   Peso total {gw} kg   ·   CBM {cbm}",
    },
    "en": {
        "empresa": "YIWU YUDA TRADING CO.,LTD",
        "cols": [
            "N°",
            "Receipt date",
            "Shipping mark",
            "Photo",
            "Reference",
            "Code",
            "Descripción (Español)",
            "Description (English)",
            "描述 (中文)",
            "Material",
            "Use",
            "Boxes",
            "Units/Box",
            "Unit",
            "Total quantity",
            "Price RMB",
            "Total RMB",
            "Price USD",
            "Total USD",
            "Length cm",
            "Width cm",
            "Height cm",
            "CBM",
            "T.CBM",
            "Weight kg",
            "Total weight kg",
            "MOQ (min. boxes)",
            "Brand",
        ],
        "numero": "Quotation No.",
        "emision": "Issue date",
        "cliente": "Client",
        "totales": "TOTALS",
        "nota": "Prices are subject to supplier confirmation.",
        "resumen": "SUMMARY:   {n} products   ·   {cajas} boxes   ·   Total USD ${usd}   ·   Total weight {gw} kg   ·   CBM {cbm}",
    },
    "zh": {
        "empresa": "义乌市与达贸易有限公司",
        "cols": [
            "序号",
            "收货日期",
            "唛头",
            "图片",
            "参考号",
            "货号",
            "描述 (西班牙语)",
            "描述 (英语)",
            "描述 (中文)",
            "材质",
            "用途",
            "箱数",
            "每箱数量",
            "单位",
            "总数量",
            "单价(元)",
            "总价(元)",
            "单价(USD)",
            "总价(USD)",
            "长 cm",
            "宽 cm",
            "高 cm",
            "CBM",
            "总CBM",
            "毛重kg",
            "总毛重kg",
            "起订量(箱)",
            "品牌",
        ],
        "numero": "报价单号",
        "emision": "签发日期",
        "cliente": "客户",
        "totales": "合计",
        "nota": "价格以供应商确认为准。",
        "resumen": "汇总：   {n} 件产品   ·   {cajas} 箱   ·   总计 USD ${usd}   ·   总毛重 {gw} kg   ·   CBM {cbm}",
    },
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

    # Logo de YUDA, sobre fondo blanco: el lockup tiene el texto en negro y no se
    # lee sobre el azul del encabezado.
    ws.merge_cells(f"A1:{ultima_col}1")
    ws.row_dimensions[1].height = 42
    logo = _logo_bytes()
    if logo is not None:
        try:
            img_logo = XLImage(BytesIO(logo))
            escala = 46 / img_logo.height
            img_logo.width = round(img_logo.width * escala)
            img_logo.height = 46
            ws.add_image(img_logo, "A1")
        except Exception:
            ws["A1"] = lab["empresa"]

    # Encabezado de empresa
    ws.merge_cells(f"A2:{ultima_col}2")
    ws["A2"] = lab["empresa"]
    ws["A2"].fill = fill_empresa
    ws["A2"].font = font_empresa
    ws["A2"].alignment = centro
    ws.merge_cells(f"A3:{ultima_col}3")
    ws["A3"] = CONTACTO["razon"]
    ws["A3"].fill = fill_empresa
    ws["A3"].font = Font(color="FFFFFF")
    ws["A3"].alignment = centro

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

    # Headers de columnas
    fila_head = 12
    for idx, titulo in enumerate(lab["cols"], start=1):
        celda = ws.cell(row=fila_head, column=idx, value=titulo)
        celda.fill = fill_head
        celda.font = font_head
        celda.alignment = centro

    # Filas de datos
    fila = fila_head + 1
    tot_cajas = tot_rmb = tot_usd = tot_cbm = tot_gw = 0.0
    for n, item in enumerate(items, start=1):
        calc = _calcular(item, tipo_cambio)
        valores = [
            n,
            item.fecha_recibo,
            sesion.shipping_mark,
            None,  # Foto (se agrega como imagen)
            item.referencia,  # referencia de catálogo de YUDA (solo cliente)
            item.item_no,
            item.descripcion_es,
            item.descripcion_en,
            item.descripcion_zh,
            item.material,
            item.uso,
            item.ctns,
            item.qty_por_ctn,
            UNIDAD,
            calc["t_qty"],
            item.price_rmb,
            calc["total_rmb"],
            calc["price_usd"],
            calc["total_usd"],
            item.largo_cm or None,
            item.ancho_cm or None,
            item.alto_cm or None,
            calc["cbm"],
            calc["t_cbm"],
            item.gw or None,
            round((item.gw or 0) * (item.ctns or 0), 2) or None,
            item.moq_cajas,
            item.marca,
        ]
        for idx, val in enumerate(valores, start=1):
            celda = ws.cell(row=fila, column=idx, value=val)
            celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if n % 2 == 0:
                celda.fill = fill_alt
        ws.row_dimensions[fila].height = 90

        # Foto: la final (limpia) si existe; si no, la de datos como respaldo.
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        if foto_doc:
            buf = _descargar_imagen(foto_doc)
            if buf is not None:
                try:
                    img = XLImage(buf)
                    img.width = 110
                    img.height = 110
                    ws.add_image(img, f"D{fila}")
                except Exception:
                    pass

        tot_cajas += item.ctns or 0
        tot_rmb += calc["total_rmb"]
        tot_usd += calc["total_usd"]
        tot_cbm += calc["t_cbm"]
        tot_gw += round((item.gw or 0) * (item.ctns or 0), 2)
        fila += 1

    # Fila de totales (las columnas van corridas por la de Referencia)
    ws.cell(row=fila, column=1, value=lab["totales"])
    ws.cell(row=fila, column=12, value=int(tot_cajas))   # Cajas
    ws.cell(row=fila, column=17, value=round(tot_rmb, 2))  # Total RMB
    ws.cell(row=fila, column=19, value=round(tot_usd, 2))  # Total USD
    ws.cell(row=fila, column=24, value=round(tot_cbm, 6))  # T.CBM
    ws.cell(row=fila, column=26, value=round(tot_gw, 2))   # Peso total

    # Recuadro de resumen amigable, arriba de la tabla
    ws.merge_cells(f"A11:{ultima_col}11")
    ws["A11"] = lab["resumen"].format(
        n=len(items),
        cajas=int(tot_cajas),
        usd=round(tot_usd, 2),
        gw=round(tot_gw, 2),
        cbm=round(tot_cbm, 6),
    )
    ws["A11"].fill = PatternFill(start_color="EEF0FD", end_color="EEF0FD", fill_type="solid")
    ws["A11"].font = Font(bold=True, color="4B52E8", size=11)
    ws["A11"].alignment = centro
    ws.row_dimensions[11].height = 24
    for col in range(1, ncols + 1):
        c = ws.cell(row=fila, column=col)
        c.fill = fill_tot
        c.font = font_tot

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
    anchos = [
        5, 13, 13, 18, 13, 12,      # N°, fecha recibo, shipping mark, foto, referencia, código
        30, 30, 24,                 # descripciones es / en / zh
        13, 16,                     # material, uso
        7, 9, 7, 11,                # cajas, uds/caja, unidad, cantidad total
        10, 11, 10, 11,             # precios y totales
        8, 8, 8,                    # largo, ancho, alto
        8, 9, 8, 11, 11, 14,        # cbm, t.cbm, pesos, mqt, marca
    ]
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
    tot_cajas = tot_rmb = tot_usd = tot_cbm = tot_gw = 0.0
    for n, item in enumerate(items, start=1):
        calc = _calcular(item, tipo_cambio)
        gw_total = round((item.gw or 0) * (item.ctns or 0), 2)
        foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        foto = f'<img src="{foto_doc}" />' if foto_doc else ""
        alt = ' class="alt"' if n % 2 == 0 else ""
        filas_html.append(
            f"<tr{alt}>"
            f"<td>{n}</td>"
            f"<td>{item.fecha_recibo or ''}</td>"
            f"<td>{sesion.shipping_mark or ''}</td>"
            f'<td class="foto">{foto}</td>'
            f"<td>{item.referencia or ''}</td>"
            f"<td>{item.item_no or ''}</td>"
            f'<td class="desc">{item.descripcion_es or ""}</td>'
            f'<td class="desc">{item.descripcion_en or ""}</td>'
            f'<td class="desc">{item.descripcion_zh or ""}</td>'
            f"<td>{item.material or ''}</td>"
            f"<td>{item.uso or ''}</td>"
            f"<td>{item.ctns or 0}</td>"
            f"<td>{item.qty_por_ctn or 0}</td>"
            f"<td>{UNIDAD}</td>"
            f"<td>{calc['t_qty']}</td>"
            f"<td>{item.price_rmb or 0}</td>"
            f"<td>{calc['total_rmb']}</td>"
            f"<td>{calc['price_usd']}</td>"
            f"<td>{calc['total_usd']}</td>"
            f"<td>{item.largo_cm or ''}</td>"
            f"<td>{item.ancho_cm or ''}</td>"
            f"<td>{item.alto_cm or ''}</td>"
            f"<td>{calc['cbm']}</td>"
            f"<td>{calc['t_cbm']}</td>"
            f"<td>{item.gw or ''}</td>"
            f"<td>{gw_total or ''}</td>"
            f"<td>{item.moq_cajas if item.moq_cajas is not None else ''}</td>"
            f"<td>{item.marca or ''}</td>"
            f"</tr>"
        )
        tot_cajas += item.ctns or 0
        tot_rmb += calc["total_rmb"]
        tot_usd += calc["total_usd"]
        tot_cbm += calc["t_cbm"]
        tot_gw += gw_total

    headers_html = "".join(f"<th>{c}</th>" for c in lab["cols"])

    logo = _logo_bytes()
    logo_html = (
        f'<div class="logo"><img src="data:image/png;base64,'
        f'{base64.b64encode(logo).decode()}" /></div>'
        if logo
        else ""
    )
    aviso_html = "".join(f"<p>{linea}</p>" for linea in AVISO_AGENCIA)
    nota = lab["nota"]

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  @page {{ size: A3 landscape; margin: 1cm; }}
  * {{ font-family: Arial, "Noto Sans CJK SC", sans-serif; }}
  body {{ color: #0D0D0D; font-size: 8px; }}
  .empresa {{ background: #1E3A5F; color: #fff; padding: 12px; text-align: center; }}
  .empresa h1 {{ margin: 0; font-size: 18px; }}
  .empresa p {{ margin: 2px 0 0; font-size: 10px; }}
  .datos {{ margin: 10px 0; font-size: 10px; }}
  .datos div {{ margin: 2px 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #4B52E8; color: #fff; padding: 4px; font-size: 8px; }}
  td {{ border: 1px solid #E5E7EB; padding: 3px; text-align: center; }}
  td.desc {{ text-align: left; }}
  .logo {{ text-align: center; padding: 6px 0; }}
  .logo img {{ height: 34px; }}
  .aviso {{ border: 1px solid #C00000; color: #C00000; font-weight: bold; font-size: 8px;
            padding: 6px 8px; margin: 8px 0; line-height: 1.35; }}
  .aviso p {{ margin: 0 0 3px; }}
  tr.alt td {{ background: #F5F5F0; }}
  td.foto img {{ max-width: 90px; max-height: 90px; }}
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
      <tr class="totales">
        <td colspan="11">{lab['totales']}</td>
        <td>{int(tot_cajas)}</td><td></td><td></td><td></td>
        <td></td><td>{round(tot_rmb, 2)}</td><td></td><td>{round(tot_usd, 2)}</td>
        <td></td><td></td><td></td>
        <td></td><td>{round(tot_cbm, 6)}</td>
        <td></td><td>{round(tot_gw, 2)}</td>
        <td></td><td></td>
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

    return render_pdf(html)
