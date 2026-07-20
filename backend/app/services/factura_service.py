"""Generación de la factura comercial en USD para el cliente.

Replica el formato exacto que usa Marcela (archivo `FORMATO FACTURA`): documento
comercial en inglés, emisor Y&H IMPORT & EXPORT CO.,LTD con su bloque bancario.
Respecto al packing list se ELIMINAN foto, precio RMB, CBM y material/uso; se
CONSERVAN descripción, cajas, cantidades, precio y total en USD, más la vendedora.

Los valores de emisor/banco se toman tal cual del archivo enviado por Marcela.
"""
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from weasyprint import HTML

from app.models.sesion import Sesion

# Emisor de la factura (según el archivo FORMATO FACTURA de Marcela).
FACTURA_EMISOR = {
    "razon": "Y&H IMPORT & EXPORT CO.,LTD",
    "direccion": (
        "ROOM 905, BUILDING 2, SHUANGCHUANG BUILDING, 1255 CHOUZHOU NORTH ROAD, "
        "FUTIAN STREET, YIWU CITY, ZHEJIANG PROVINCE"
    ),
    "tel": "+(86)-579-85340206",
    "usci": "91330782MA2JWGPU0R",
    "terms": "FOB-NINGBO",
}

# Bloque de pago / datos bancarios (según el archivo FORMATO FACTURA de Marcela).
FACTURA_BANCO = {
    "payment": "100% T/T IN ADVANCE, BALANCE T/T AGAINST BEFORE LOADING THE CONTAINER",
    "intermediary_bank": "BANK OF AMERICA N.A. NEW YORK (SWIFT CODE: BOFAUS3N)",
    "beneficiary_bank": "ZHEJIANG CHOUZHOU COMMERCIAL BANK CO.,LTD",
    "swift_bic": "CZCBCN2X",
    "bank_address": "NO.161 Bayi South Street Jinhua City Zhejiang Province China",
    "beneficiary_name": "Y AND H IMPORT AND EXPORT CO.,LTD",
    "account_no": "NRA15701142010500026376",
    "beneficiary_address": (
        "ROOM 905, BUILDING 2, SHUANGCHUANG BUILDING, 1255 CHOUZHOU NORTH ROAD, "
        "FUTIAN STREET, YIWU CITY, ZHEJIANG PROVINCE"
    ),
    "shipping_marks": "ACCORDING TO INSTRUCTION",
    "more_or_less": "QUANTITY AND AMOUNT +-10% ALLOWED",
}

# Columnas de la factura (equivalen a las del archivo real).
COLS_FACTURA = ["N°", "ITEM No.", "DESCRIPTION", "CTN", "QTY", "TOTAL QTY", "UNIT (USD)", "AMOUNT"]


def numero_factura(sesion: Sesion, fecha: datetime) -> str:
    """Número de factura determinístico y único por cotización."""
    return f"YUDA-INV-{fecha.strftime('%Y%m%d')}-{sesion.id[:6].upper()}"


def _fila_calc(item, trm: float) -> dict:
    """Cantidades y montos en USD de un ítem para la factura."""
    ctn = item.ctns or 0
    qty = item.qty_por_ctn or 0
    total_qty = ctn * qty
    unit_usd = round((item.price_rmb or 0) / trm, 4) if trm else 0.0
    amount_usd = round(unit_usd * total_qty, 2)
    return {"ctn": ctn, "qty": qty, "total_qty": total_qty, "unit_usd": unit_usd, "amount_usd": amount_usd}


def _descripcion(item) -> str:
    """Descripción en inglés (la factura es un documento comercial en inglés)."""
    return item.descripcion_en or item.descripcion_es or ""


def generar_factura_pdf(
    items: list, sesion: Sesion, trm: float, vendedora: str | None = None
) -> bytes:
    """Genera la factura comercial en USD (PDF) con WeasyPrint."""
    fecha = datetime.now()
    numero = numero_factura(sesion, fecha)

    filas_html = []
    tot_ctn = tot_qty = tot_amount = 0.0
    for n, item in enumerate(items, start=1):
        c = _fila_calc(item, trm)
        alt = ' class="alt"' if n % 2 == 0 else ""
        filas_html.append(
            f"<tr{alt}>"
            f"<td>{n}</td>"
            f"<td>{item.item_no or ''}</td>"
            f'<td class="desc">{_descripcion(item)}</td>'
            f"<td>{c['ctn']}</td>"
            f"<td>{c['qty']}</td>"
            f"<td>{c['total_qty']}</td>"
            f"<td>{c['unit_usd']}</td>"
            f"<td>{c['amount_usd']}</td>"
            f"</tr>"
        )
        tot_ctn += c["ctn"]
        tot_qty += c["total_qty"]
        tot_amount += c["amount_usd"]

    headers_html = "".join(f"<th>{c}</th>" for c in COLS_FACTURA)
    vendedora_html = (
        f'<div><strong>SALESPERSON:</strong> {vendedora}</div>' if vendedora else ""
    )
    b = FACTURA_BANCO

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  @page {{ size: A4; margin: 1.4cm; }}
  * {{ font-family: Arial, sans-serif; }}
  body {{ color: #0D0D0D; font-size: 10px; }}
  .head {{ display: flex; justify-content: space-between; align-items: flex-start; }}
  .emisor h1 {{ margin: 0; font-size: 15px; color: #1E3A5F; }}
  .emisor p {{ margin: 1px 0; font-size: 9px; max-width: 340px; }}
  .meta {{ text-align: right; font-size: 10px; }}
  .titulo {{ text-align: center; font-size: 20px; font-weight: bold; letter-spacing: 3px; margin: 14px 0; }}
  .to {{ margin: 6px 0; font-size: 10px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th {{ background: #1E3A5F; color: #fff; padding: 5px; font-size: 9px; }}
  td {{ border: 1px solid #E5E7EB; padding: 4px; text-align: center; }}
  td.desc {{ text-align: left; }}
  tr.alt td {{ background: #F5F5F0; }}
  tr.totales td {{ background: #0D0D0D; color: #fff; font-weight: bold; }}
  .banco {{ margin-top: 14px; font-size: 9px; line-height: 1.5; }}
  .banco strong {{ display: inline-block; min-width: 150px; }}
  .firma {{ margin-top: 40px; font-size: 10px; }}
</style></head><body>
  <div class="head">
    <div class="emisor">
      <h1>{FACTURA_EMISOR['razon']}</h1>
      <p>{FACTURA_EMISOR['direccion']}</p>
      <p>Tel: {FACTURA_EMISOR['tel']} · USCI: {FACTURA_EMISOR['usci']}</p>
    </div>
    <div class="meta">
      <div><strong>INVOICE No:</strong> {numero}</div>
      <div><strong>DATE:</strong> {fecha.strftime('%Y-%m-%d')}</div>
      <div><strong>TERMS:</strong> {FACTURA_EMISOR['terms']}</div>
    </div>
  </div>
  <div class="titulo">INVOICE</div>
  <div class="to">
    <div><strong>TO:</strong> {sesion.nombre_cliente}</div>
    {vendedora_html}
  </div>
  <table>
    <thead><tr>{headers_html}</tr></thead>
    <tbody>
      {''.join(filas_html)}
      <tr class="totales">
        <td colspan="3">TOTAL</td>
        <td>{int(tot_ctn)}</td>
        <td></td>
        <td>{int(tot_qty)}</td>
        <td>TOTAL USD:</td>
        <td>{round(tot_amount, 2)}</td>
      </tr>
    </tbody>
  </table>
  <div class="banco">
    <div><strong>PAYMENT:</strong> {b['payment']}</div>
    <div><strong>INTERMEDIARY BANK:</strong> {b['intermediary_bank']}</div>
    <div><strong>BENEFICIARY BANK:</strong> {b['beneficiary_bank']}</div>
    <div><strong>SWIFT BIC:</strong> {b['swift_bic']}</div>
    <div><strong>BANK ADDRESS:</strong> {b['bank_address']}</div>
    <div><strong>BENEFICIARY NAME:</strong> {b['beneficiary_name']}</div>
    <div><strong>A/C NO:</strong> {b['account_no']}</div>
    <div><strong>ADDRESS:</strong> {b['beneficiary_address']}</div>
    <div><strong>SHIPPING MARKS:</strong> {b['shipping_marks']}</div>
    <div><strong>MORE OR LESS:</strong> {b['more_or_less']}</div>
  </div>
  <div class="firma">AUTHORIZED SIGNING: ____________________________</div>
</body></html>"""

    return HTML(string=html).write_pdf()


def generar_factura_excel(
    items: list, sesion: Sesion, trm: float, vendedora: str | None = None
) -> bytes:
    """Genera la factura comercial en USD (Excel)."""
    fecha = datetime.now()
    numero = numero_factura(sesion, fecha)

    wb = Workbook()
    ws = wb.active
    ws.title = "INVOICE"

    fill_emisor = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    font_emisor = Font(color="FFFFFF", bold=True, size=13)
    fill_head = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    font_head = Font(color="FFFFFF", bold=True)
    fill_tot = PatternFill(start_color="0D0D0D", end_color="0D0D0D", fill_type="solid")
    font_tot = Font(color="FFFFFF", bold=True)
    centro = Alignment(horizontal="center", vertical="center")

    ncols = len(COLS_FACTURA)  # 8 → col H
    ultima = "H"

    ws.merge_cells(f"A1:{ultima}1")
    ws["A1"] = FACTURA_EMISOR["razon"]
    ws["A1"].fill = fill_emisor
    ws["A1"].font = font_emisor
    ws["A1"].alignment = centro
    ws.merge_cells(f"A2:{ultima}2")
    ws["A2"] = FACTURA_EMISOR["direccion"]
    ws["A2"].alignment = Alignment(horizontal="center", wrap_text=True)

    ws["A4"] = f"INVOICE No: {numero}"
    ws["A5"] = f"DATE: {fecha.strftime('%Y-%m-%d')}"
    ws["A6"] = f"TERMS: {FACTURA_EMISOR['terms']}"
    ws["A7"] = f"TO: {sesion.nombre_cliente}"
    if vendedora:
        ws["A8"] = f"SALESPERSON: {vendedora}"

    fila_head = 10
    for idx, titulo in enumerate(COLS_FACTURA, start=1):
        celda = ws.cell(row=fila_head, column=idx, value=titulo)
        celda.fill = fill_head
        celda.font = font_head
        celda.alignment = centro

    fila = fila_head + 1
    tot_ctn = tot_qty = tot_amount = 0.0
    for n, item in enumerate(items, start=1):
        c = _fila_calc(item, trm)
        ws.cell(row=fila, column=1, value=n)
        ws.cell(row=fila, column=2, value=item.item_no or "")
        ws.cell(row=fila, column=3, value=_descripcion(item))
        ws.cell(row=fila, column=4, value=c["ctn"])
        ws.cell(row=fila, column=5, value=c["qty"])
        ws.cell(row=fila, column=6, value=c["total_qty"])
        ws.cell(row=fila, column=7, value=c["unit_usd"])
        ws.cell(row=fila, column=8, value=c["amount_usd"])
        tot_ctn += c["ctn"]
        tot_qty += c["total_qty"]
        tot_amount += c["amount_usd"]
        fila += 1

    # Fila de totales
    for col in range(1, ncols + 1):
        ws.cell(row=fila, column=col).fill = fill_tot
        ws.cell(row=fila, column=col).font = font_tot
    ws.cell(row=fila, column=1, value="TOTAL")
    ws.cell(row=fila, column=4, value=int(tot_ctn))
    ws.cell(row=fila, column=6, value=int(tot_qty))
    ws.cell(row=fila, column=7, value="TOTAL USD:")
    ws.cell(row=fila, column=8, value=round(tot_amount, 2))

    # Bloque bancario
    fila += 2
    b = FACTURA_BANCO
    lineas = [
        ("PAYMENT", b["payment"]),
        ("INTERMEDIARY BANK", b["intermediary_bank"]),
        ("BENEFICIARY BANK", b["beneficiary_bank"]),
        ("SWIFT BIC", b["swift_bic"]),
        ("BANK ADDRESS", b["bank_address"]),
        ("BENEFICIARY NAME", b["beneficiary_name"]),
        ("A/C NO", b["account_no"]),
        ("ADDRESS", b["beneficiary_address"]),
        ("SHIPPING MARKS", b["shipping_marks"]),
        ("MORE OR LESS", b["more_or_less"]),
    ]
    for etq, val in lineas:
        ws.cell(row=fila, column=1, value=f"{etq}:")
        ws.cell(row=fila, column=1).font = Font(bold=True)
        ws.merge_cells(start_row=fila, start_column=3, end_row=fila, end_column=ncols)
        ws.cell(row=fila, column=3, value=val)
        fila += 1

    # Anchos de columna
    anchos = {"A": 6, "B": 14, "C": 40, "D": 8, "E": 8, "F": 12, "G": 12, "H": 14}
    for col, ancho in anchos.items():
        ws.column_dimensions[col].width = ancho

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
