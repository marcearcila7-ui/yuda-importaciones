"""Generación del PDF de Formato Pedido (documento para el proveedor).

Réplica fiel del formato FORMATO PEDIDO de YUDA: membrete, tabla con
encabezados bilingües, totales y las notas/condiciones/firmas. Se genera a
partir de los datos (no editable), para enviar al proveedor sin que lo alteren.
"""
from datetime import date

from weasyprint import HTML

PED_CSS = """
@page { size: A4 landscape; margin: 0.8cm; }
* { font-family: 'Noto Sans CJK SC', 'Arial', sans-serif; box-sizing: border-box; }
.empresa { text-align: center; font-size: 16px; font-weight: bold; }
.cab { width: 100%; border-collapse: collapse; margin-bottom: 4px; font-size: 9px; }
.cab td { border: 1px solid #999; padding: 3px 5px; }
table.items { width: 100%; border-collapse: collapse; font-size: 9px; }
table.items th { background: #404040; color: #fff; padding: 4px 3px; border: 1px solid #555; white-space: pre-line; }
table.items td { padding: 3px; border: 1px solid #999; text-align: center; vertical-align: middle; }
/* Un producto no se parte entre dos páginas: si no cabe, pasa entero a la
   siguiente. Sin esto la foto quedaba sola en una página, sin sus datos. */
table.items tbody tr { page-break-inside: avoid; break-inside: avoid; }
table.items td.desc { text-align: left; }
/* La foto es la referencia de lo que se pidió: va grande y completa (contain,
   sin recortar), y su celda manda el ancho de la columna. */
table.items td.foto { width: 175px; }
table.items td.foto img { width: 165px; height: 165px; object-fit: contain; }
/* ITEM NO se rellena a mano sobre el impreso: necesita ancho propio. */
table.items td.item, table.items th.item { width: 90px; }
table.items td.desc .zh { display: block; }
tr.total td { background: #EEE; font-weight: bold; }
.firmas { margin-top: 6px; font-size: 10px; border: 1px solid #999; padding: 6px; }
.notas { margin-top: 4px; font-size: 8px; }
/* Las firmas y el bloque de condiciones/marcado van enteros: sin esto se
   partían y quedaba una página suelta con tres líneas del marcado. */
.firmas, .notas, .notas tr, .marca { page-break-inside: avoid; break-inside: avoid; }
.notas td { vertical-align: top; padding: 2px 6px; }
.marca { border: 1px solid #999; padding: 4px; font-size: 8px; }
.marca-inicial { border: 2px solid #000; padding: 4px 8px; font-size: 16px; font-weight: bold;
  text-align: center; margin-bottom: 4px; }
"""

# CSS del Packing List interno (documento para el CLIENTE). Bug preexistente
# encontrado al agregar las columnas de bolso: esta constante se llamaba "CSS"
# hasta que el commit 520d415 la renombró a PED_CSS para el pedido al proveedor
# y no actualizó la referencia en generar_packing_list_pdf, que quedó rota
# (NameError) desde entonces — la descarga en PDF del Packing List al cliente
# nunca funcionó desde ese commit. Se restaura con nombre propio.
PACKING_CSS = """
@page { size: A4 landscape; margin: 1.2cm; }
* { font-family: 'Helvetica', 'Arial', sans-serif; }
.empresa { text-align: center; font-size: 14px; font-weight: bold; color: #0D0D0D; }
.sub { text-align: center; font-size: 10px; color: #444; margin-bottom: 2px; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9px; }
th { background: #404040; color: #fff; padding: 5px 4px; border: 1px solid #555; }
td { padding: 4px; border: 1px solid #ccc; text-align: center; vertical-align: middle; }
td.desc { text-align: left; }
td.foto img { width: 50px; height: 50px; object-fit: cover; }
/* Fotos de detalle del bolso (interior/herrajes/riata/exterior): van más chicas
   que la foto principal, si no la tabla de bolsos no entra ni en A4 apaisado. */
td.foto-extra img { width: 36px; height: 36px; object-fit: cover; }
tr.alt td { background: #F7F7FA; }
tr.total td { background: #EEE; font-weight: bold; }
"""


def render_pdf(html: str) -> bytes:
    """Renderiza un HTML a PDF.

    `hinting=True` deja los hints de la fuente tal cual: WeasyPrint se salta el
    paso de limpiarlos, que en la fuente china (Noto CJK, decenas de miles de
    glifos) se lleva un tercio del tiempo total y no cambia el resultado visible.

    Es una función a nivel de módulo (y no un closure) a propósito: así se puede
    mandar a otro proceso con ProcessPoolExecutor cuando hay que generar varios
    PDFs a la vez.
    """
    return HTML(string=html).write_pdf(hinting=True)


def html_pedido(
    supplier_nombre: str, supplier_numero: str, items: list, fecha: date,
    fotos: dict | None = None, shipping_mark: str | None = None,
) -> str:
    """Arma el HTML del Formato Pedido del proveedor (réplica fiel, con fotos).

    `fotos` mapea url→data URI (imagen ya descargada e incrustada). Se usa para que
    WeasyPrint NO haga peticiones de red al renderizar (evita cuelgues por fotos
    lentas). Si una foto no está en el diccionario, la fila va sin imagen.
    """
    fotos = fotos or {}
    filas = []
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
        # Un 0.0 en CBM o peso el proveedor lo lee como un dato real equivocado;
        # si no está cargado, la celda va vacía.
        cbm_txt, tcbm_txt, gw_txt = (cbm or ""), (tcbm or ""), (gw or "")

        tot_ctn += ctn
        tot_qty += qty
        tot_amount += amount
        tot_tcbm += tcbm

        # Descripción SIEMPRE en español y en chino: la vendedora escribe en
        # español y el proveedor lee el chino.
        _es = item.descripcion_es or item.descripcion_en or ""
        _zh = item.descripcion_zh or ""
        desc = _es + (f'<span class="zh">{_zh}</span>' if _zh else "")
        # Foto final (limpia) si existe; si no, la de datos como respaldo.
        # Se usa la imagen YA descargada e incrustada (data URI); sin red al renderizar.
        _foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        _data = fotos.get(_foto_doc) if _foto_doc else None
        foto = f'<img src="{_data}" />' if _data else ""
        filas.append(
            f"<tr>"
            f"<td>{n}</td>"
            f'<td class="foto">{foto}</td>'
            f'<td class="item">{item.item_no or ""}</td>'
            f'<td class="desc">{desc}</td>'
            f"<td>{ctn}</td><td>{qty_ctn}</td><td>PCS</td><td>{qty}</td>"
            f"<td>{price}</td><td>{round(amount, 2)}</td>"
            f"<td>{cbm_txt}</td><td>{tcbm_txt}</td><td>{gw_txt}</td>"
            f"</tr>"
        )

    encab = (
        "<tr>"
        "<th>NO\n序号</th><th>PHOTO\n产品照片</th><th>ITEM NO\n客户货号</th>"
        "<th>DESCRIPTION\n品名及规格</th><th>CTN\n箱数</th><th>QTY/CTN\n装箱数</th>"
        "<th>UNIT</th><th>QTY\n总数量</th><th>PRICE\n单价</th><th>AMOUNT\n金额</th>"
        "<th>CBM\n箱规</th><th>T.CBM\n总体积</th><th>G.W\n毛重</th>"
        "</tr>"
    )
    total = (
        f'<tr class="total"><td colspan="4">Total Amount（总金额）¥</td>'
        f"<td>{int(tot_ctn)}</td><td></td><td></td><td>{int(tot_qty)}</td>"
        f"<td></td><td>{round(tot_amount, 2)}</td><td></td><td>{round(tot_tcbm, 6) or ''}</td><td></td></tr>"
    )

    terminos = (
        "1.质量要求技术标准：产品品质、规格应完全与样品及合同要求相符.否则拒绝收货<br>"
        "2.买方已付订金或订单被卖方取消时，卖方需返还三倍订金作为买方损失.<br>"
        "3.订单的任何变更需取得买方经理的认可.未经买方经理认可，对订单的修改将不被买方接受.<br>"
        "4.供方必须按照买方签订的时间准时交货.若不能如期交货，一切责任由供货方承担.<br>"
        "5.货品要保质、保量、不良货品可以退掉."
    )
    # La marca (iniciales del cliente) es con lo que el proveedor separa las
    # cajas de cada pedido en su bodega para no confundirlas; en el papel va
    # dentro de un rombo dibujado a mano, acá es una caja destacada en el mismo
    # lugar (antes de "两张正唛/两张侧唛"), que es lo que de verdad hace falta ver.
    marca_inicial = f'<div class="marca-inicial">{shipping_mark.strip().upper()}</div>' if shipping_mark else ""
    marca = (
        f"{marca_inicial}"
        "两张正唛 / 两张侧唛<br>ITEM NO.: 客户货号<br>QTY.: 装箱数 PCS<br>"
        "G.W.: 毛重 KGS<br>N.W.: KGS<br>MEAS.: X X CM<br>"
        "普货用五层硬纸箱 重大货加套编织袋<br>易碎液体等产品请贴向上易碎标<br>"
        "所有产品交货时都需要每款每色验货"
    )

    cabecera = f"""
    <p class="empresa">义乌市与达贸易有限公司</p>
    <table class="cab"><tr>
      <td>BOOTH(店面)：17907<br>TEL(电话)：18806893598<br>CONTACT(联系人)：小何<br>PAYMENT TIME(付款时间)：30天（节假日除外）</td>
      <td>ORDER DATE(订货日期)：____年__月__日<br>DELIVERY DATE(交货日期)：____年__月__日<br>DELIVERY ADD(交货地址)：<br>CLIENTE(客户)：</td>
      <td>地址(add)：浙江省义乌市稠州北路1121号<br>福田大厦A座0909-0911室<br>电话：+86 18058944598<br>工作时间：周一到周五9:00-17:00</td>
    </tr></table>
    """

    html = f"""<html><head><meta charset="utf-8"><style>{PED_CSS}</style></head><body>
      {cabecera}
      <table class="items"><thead>{encab}</thead><tbody>{''.join(filas)}{total}</tbody></table>
      <div class="firmas">Total Amount（总金额）：____拾____万____仟____佰____拾____元　　¥：__________<br><br>
        采购方签名（Buyer Signature）：______________________　　　供货方签名（Seller Signature）：______________________</div>
      <table class="notas"><tr>
        <td style="width:65%"><b>注意事项：</b><br>{terminos}</td>
        <td class="marca">{marca}</td>
      </tr></table>
    </body></html>"""

    return html


def generar_pedido_pdf(
    supplier_nombre: str, supplier_numero: str, items: list, fecha: date,
    fotos: dict | None = None,
) -> bytes:
    """PDF del Formato Pedido de un proveedor (arma el HTML y lo renderiza)."""
    return render_pdf(html_pedido(supplier_nombre, supplier_numero, items, fecha, fotos))


def generar_packing_list_pdf(
    items: list, sesion_nombre_cliente: str, tipo_cambio_usd: float,
    tipo_cotizacion: str = "productos",
) -> bytes:
    """Genera el PDF del Packing List interno (con fotos) y devuelve sus bytes.

    En modo bolsos agrega columnas propias (colores, tamaño, empaque, etiqueta,
    herrajes, riata, los dos mínimos de tienda) al final; en productos varios el
    PDF queda exactamente igual que siempre.
    """
    es_bolsos = tipo_cotizacion == "bolsos"
    tc = tipo_cambio_usd or 1
    filas_html = []
    tot_ctns = tot_rmb = tot_usd = tot_tcbm = tot_tgw = 0.0

    # Fotos de detalle del bolso (item.fotos_extra), mismo orden que sus columnas.
    tipos_foto_extra = ["interior", "herrajes", "riata", "exterior"]

    for n, item in enumerate(items, start=1):
        ctns = item.ctns or 0
        qty_ctn = item.qty_por_ctn or 0
        t_qty = ctns * qty_ctn
        price = item.price_rmb or 0
        total_rmb = price * t_qty
        price_usd = round(price / tc, 4)
        total_usd = round(price_usd * t_qty, 2)
        largo = item.largo_cm or 0
        ancho = item.ancho_cm or 0
        alto = item.alto_cm or 0
        cbm = round(largo * ancho * alto / 1_000_000, 6)
        t_cbm = round(cbm * ctns, 6)
        gw = item.gw or 0
        t_gw = round(gw * ctns, 2)

        tot_ctns += ctns
        tot_rmb += total_rmb
        tot_usd += total_usd
        tot_tcbm += t_cbm
        tot_tgw += t_gw

        # Foto final (recortada a mano o por el OCR) si existe; si no, la original.
        _foto_doc = getattr(item, "foto_final_url", None) or getattr(item, "foto_url", None)
        foto = f'<img src="{_foto_doc}" />' if _foto_doc else ""
        alt = ' class="alt"' if n % 2 == 0 else ""
        cols_bolsos = ""
        if es_bolsos:
            fotos_extra_item = getattr(item, "fotos_extra", None) or {}
            fotos_extra_html = ""
            for tipo_foto in tipos_foto_extra:
                url = fotos_extra_item.get(tipo_foto)
                img_extra = f'<img src="{url}" />' if url else ""
                fotos_extra_html += f'<td class="foto-extra">{img_extra}</td>'
            cols_bolsos = (
                f"<td>{getattr(item, 'colores', None) or ''}</td>"
                f"<td>{getattr(item, 'tamano', None) or ''}</td>"
                f"<td>{getattr(item, 'empaque', None) or ''}</td>"
                f"<td>{getattr(item, 'etiqueta', None) or ''}</td>"
                f"<td>{getattr(item, 'herrajes', None) or ''}</td>"
                f"<td>{getattr(item, 'riata', None) or ''}</td>"
                f"<td>{getattr(item, 'minimo_cajas_tienda', None) or ''}</td>"
                f"<td>{getattr(item, 'minimo_piezas_caja_tienda', None) or ''}</td>"
                f"{fotos_extra_html}"
            )
        filas_html.append(
            f"<tr{alt}>"
            f"<td>{n}</td>"
            f'<td class="foto">{foto}</td>'
            f"<td>{item.supplier_nombre or ''}</td>"
            f"<td>{item.item_no or ''}</td>"
            f'<td class="desc">{item.descripcion_es or item.descripcion_en or ""}</td>'
            f"<td>{ctns}</td>"
            f"<td>{qty_ctn}</td>"
            f"<td>{t_qty}</td>"
            f"<td>{price}</td>"
            f"<td>{round(total_rmb, 2)}</td>"
            f"<td>{price_usd}</td>"
            f"<td>{total_usd}</td>"
            f"<td>{cbm}</td>"
            f"<td>{t_cbm}</td>"
            f"<td>{gw}</td>"
            f"<td>{t_gw}</td>"
            f"{cols_bolsos}"
            f"</tr>"
        )

    encab_bolsos = (
        "<th>COLORES</th><th>TAMAÑO</th><th>EMPAQUE</th><th>ETIQUETA</th>"
        "<th>HERRAJES</th><th>RIATA</th><th>MÍN. CAJAS<br>(TIENDA)</th>"
        "<th>MÍN. PZS/CAJA<br>(TIENDA)</th>"
        "<th>FOTO<br>INTERIOR</th><th>FOTO<br>HERRAJES</th>"
        "<th>FOTO<br>RIATA</th><th>FOTO<br>EXTERIOR</th>"
    ) if es_bolsos else ""
    encabezado = (
        "<tr><th>N°</th><th>FOTO</th><th>PROVEEDOR</th><th>N° ÍTEM</th><th>DESCRIPCIÓN</th>"
        "<th>CAJAS</th><th>UN/CAJA</th><th>T.UN</th><th>PRECIO ¥</th><th>TOTAL ¥</th>"
        "<th>PRECIO $</th><th>TOTAL $</th><th>CBM</th><th>T.CBM</th><th>GW</th><th>T.GW</th>"
        f"{encab_bolsos}</tr>"
    )
    total_bolsos = "<td></td>" * 12 if es_bolsos else ""
    total = (
        f'<tr class="total"><td colspan="5">TOTALES</td>'
        f"<td>{int(tot_ctns)}</td><td></td><td></td><td></td>"
        f"<td>{round(tot_rmb, 2)}</td><td></td><td>{round(tot_usd, 2)}</td>"
        f"<td></td><td>{round(tot_tcbm, 6)}</td><td></td><td>{round(tot_tgw, 2)}</td>"
        f"{total_bolsos}</tr>"
    )

    html = f"""<html><head><meta charset="utf-8"><style>{PACKING_CSS}</style></head><body>
      <p class="empresa">YUDA — Packing List</p>
      <p class="sub">{sesion_nombre_cliente} · 1 USD = {tipo_cambio_usd} RMB</p>
      <table>
        <thead>{encabezado}</thead>
        <tbody>{''.join(filas_html)}{total}</tbody>
      </table>
    </body></html>"""

    return render_pdf(html)
