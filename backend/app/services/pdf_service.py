"""Generación del PDF de Formato Pedido (documento para el proveedor)."""
from datetime import date

from weasyprint import HTML

CSS = """
@page { size: A4 landscape; margin: 1.2cm; }
* { font-family: 'Helvetica', 'Arial', sans-serif; }
.empresa { text-align: center; font-size: 14px; font-weight: bold; color: #0D0D0D; }
.sub { text-align: center; font-size: 10px; color: #444; margin-bottom: 2px; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9px; }
th { background: #404040; color: #fff; padding: 5px 4px; border: 1px solid #555; }
td { padding: 4px; border: 1px solid #ccc; text-align: center; vertical-align: middle; }
td.desc { text-align: left; }
td.foto img { width: 50px; height: 50px; object-fit: cover; }
tr.alt td { background: #F7F7FA; }
tr.total td { background: #EEE; font-weight: bold; }
"""


def generar_pedido_pdf(
    supplier_nombre: str, supplier_numero: str, items: list, fecha: date
) -> bytes:
    """Genera el PDF del Formato Pedido de un proveedor (con fotos) y devuelve sus bytes."""
    filas_html = []
    tot_ctn = tot_qty = tot_amount = tot_tcbm = 0.0

    for n, item in enumerate(items, start=1):
        ctn = item.ctns or 0
        qty_ctn = item.qty_por_ctn or 0
        qty = ctn * qty_ctn
        price = item.price_rmb or 0
        amount = price * qty
        largo = item.largo_cm or 0
        ancho = item.ancho_cm or 0
        alto = item.alto_cm or 0
        cbm = round(largo * ancho * alto / 1_000_000, 6)
        tcbm = round(cbm * ctn, 6)
        gw = item.gw or 0

        tot_ctn += ctn
        tot_qty += qty
        tot_amount += amount
        tot_tcbm += tcbm

        partes = [p for p in [item.descripcion_es, item.descripcion_en] if p]
        descripcion = " / ".join(partes)
        foto = f'<img src="{item.foto_url}" />' if getattr(item, "foto_url", None) else ""
        alt = ' class="alt"' if n % 2 == 0 else ""

        filas_html.append(
            f"<tr{alt}>"
            f"<td>{n}</td>"
            f'<td class="foto">{foto}</td>'
            f"<td>{item.item_no or ''}</td>"
            f'<td class="desc">{descripcion}</td>'
            f"<td>{ctn}</td>"
            f"<td>{qty_ctn}</td>"
            f"<td>{qty}</td>"
            f"<td>{price}</td>"
            f"<td>{round(amount, 2)}</td>"
            f"<td>{cbm}</td>"
            f"<td>{tcbm}</td>"
            f"<td>{gw}</td>"
            f"</tr>"
        )

    encabezado = (
        "<tr><th>NO</th><th>PHOTO</th><th>ITEM NO</th><th>DESCRIPTION</th>"
        "<th>CTN</th><th>QTY/CTN</th><th>QTY</th><th>PRICE</th><th>AMOUNT</th>"
        "<th>CBM</th><th>T.CBM</th><th>G.W</th></tr>"
    )
    total = (
        f'<tr class="total"><td colspan="4">Total Amount (总金额) ¥</td>'
        f"<td>{int(tot_ctn)}</td><td></td><td>{int(tot_qty)}</td><td></td>"
        f"<td>{round(tot_amount, 2)}</td><td></td><td>{round(tot_tcbm, 6)}</td><td></td></tr>"
    )

    nombre = supplier_nombre or "Sin proveedor"
    booth = f" · BOOTH: {supplier_numero}" if supplier_numero else ""

    html = f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
      <p class="empresa">YUDA — 义乌市与达贸易有限公司</p>
      <p class="sub">{nombre}{booth} · ORDER DATE: {fecha.strftime('%Y-%m-%d')}</p>
      <p class="sub">地址：义乌市稠州北路1121号福田大厦A座0909-0911室</p>
      <table>
        <thead>{encabezado}</thead>
        <tbody>{''.join(filas_html)}{total}</tbody>
      </table>
    </body></html>"""

    return HTML(string=html).write_pdf()
