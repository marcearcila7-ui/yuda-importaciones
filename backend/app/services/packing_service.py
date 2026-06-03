from app.models.item import Item


def calcular_campos_item(item: Item, tipo_cambio_usd: float) -> dict:
    """Calcula las columnas derivadas de un ítem (nunca se almacenan en DB)"""
    t_qty = item.qty_por_ctn * item.ctns
    total_rmb = item.price_rmb * t_qty
    # Protección por si el tipo de cambio fuera 0
    price_usd = round(item.price_rmb / tipo_cambio_usd, 4) if tipo_cambio_usd else 0.0
    total_usd = round(price_usd * t_qty, 4)
    cbm = round(item.largo_cm * item.ancho_cm * item.alto_cm / 1_000_000, 6)
    t_cbm = round(cbm * item.ctns, 6)
    t_gw = round(item.gw * item.ctns, 4)

    return {
        "t_qty": t_qty,
        "total_rmb": total_rmb,
        "price_usd": price_usd,
        "total_usd": total_usd,
        "cbm": cbm,
        "t_cbm": t_cbm,
        "t_gw": t_gw,
    }
