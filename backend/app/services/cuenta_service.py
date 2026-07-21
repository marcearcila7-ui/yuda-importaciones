"""Estado de cuenta de un cliente, organizado POR PEDIDO (cotización).

Cada pedido lleva su propia contabilidad: sus movimientos con saldo acumulado
propio y su subtotal. Los movimientos sin pedido caen en un apartado aparte.
Arriba se resume el total del cliente (suma de todos sus pedidos).
"""
from datetime import date

from app.models.cliente import Cliente
from app.models.cuenta import MovimientoCuenta
from app.models.sesion import Sesion


def _f(valor) -> float:
    """Numeric de SQLAlchemy → float (evita Decimal en las respuestas)."""
    return float(valor or 0)


def _orden(mov: MovimientoCuenta):
    """Orden cronológico estable: por fecha y, a igualdad, por creación."""
    return (mov.fecha or date.min, mov.created_at)


def numero_pedido(sesion: Sesion) -> str:
    """Número legible del pedido/cotización (mismo formato del portal)."""
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


def _fila(m: MovimientoCuenta, saldo: float) -> dict:
    return {
        "id": m.id,
        "cliente_id": m.cliente_id,
        "sesion_id": m.sesion_id,
        "contenedor_id": m.contenedor_id,
        "moneda": m.moneda or "USD",
        "envio": m.envio,
        "fecha": m.fecha,
        "guia": m.guia,
        "descripcion": m.descripcion,
        "valor_mercancia": round(_f(m.valor_mercancia), 2),
        "comision_yuda": round(_f(m.comision_yuda), 2),
        "abono": round(_f(m.abono), 2),
        "saldo": round(saldo, 2),
        "nota": m.nota,
        "created_at": m.created_at,
    }


def construir_estado_cuenta(
    cliente: Cliente,
    movimientos: list[MovimientoCuenta],
    sesiones: list[Sesion],
) -> dict:
    """Arma el estado de cuenta agrupado por pedido (cotización) + total cliente."""
    ses_map = {s.id: s for s in sesiones}

    # Agrupar movimientos por pedido (sesion_id); None = "sin pedido".
    grupos: dict[str | None, list[MovimientoCuenta]] = {}
    for m in movimientos:
        grupos.setdefault(m.sesion_id, []).append(m)

    # Orden: pedidos reales primero (por fecha de cotización desc), "sin pedido" al final.
    reales = [sid for sid in grupos if sid is not None]
    reales.sort(
        key=lambda sid: (ses_map[sid].fecha if sid in ses_map and ses_map[sid].fecha else date.min),
        reverse=True,
    )
    orden_sids = reales + ([None] if None in grupos else [])

    pedidos = []
    # Totales del cliente agrupados por moneda (no se mezclan monedas distintas).
    por_moneda: dict[str, dict[str, float]] = {}
    fecha_ultimo_abono: date | None = None

    for sid in orden_sids:
        movs = sorted(grupos[sid], key=_orden)
        # Moneda del pedido = la de sus movimientos (se mantiene consistente).
        moneda = (movs[0].moneda if movs and movs[0].moneda else "USD")
        compras = comision = abonos = saldo = 0.0
        filas = []
        for m in movs:
            valor, com, ab = _f(m.valor_mercancia), _f(m.comision_yuda), _f(m.abono)
            compras += valor
            comision += com
            abonos += ab
            saldo += valor + com - ab  # saldo acumulado DENTRO del pedido
            if ab > 0 and (fecha_ultimo_abono is None or (m.fecha and m.fecha > fecha_ultimo_abono)):
                fecha_ultimo_abono = m.fecha
            filas.append(_fila(m, saldo))
            mon = m.moneda or "USD"
            acc = por_moneda.setdefault(mon, {"compras": 0.0, "comision": 0.0, "abonos": 0.0})
            acc["compras"] += valor
            acc["comision"] += com
            acc["abonos"] += ab

        s = ses_map.get(sid) if sid else None
        pedidos.append(
            {
                "sesion_id": sid,
                "pedido_numero": numero_pedido(s) if s else None,
                "pedido_fecha": s.fecha if s else None,
                # "Ya es pedido" cuando la cotización entró al circuito de pedido
                # (el cliente envió/confirmó cantidades → tiene packing list).
                "es_pedido": bool(s and s.pedido_estado),
                "moneda": moneda,
                "compras_totales": round(compras, 2),
                "comision_total": round(comision, 2),
                "abonos_totales": round(abonos, 2),
                "saldo_pendiente": round(compras + comision - abonos, 2),
                "movimientos": filas,
            }
        )

    totales_por_moneda = [
        {
            "moneda": mon,
            "compras_totales": round(v["compras"], 2),
            "comision_total": round(v["comision"], 2),
            "abonos_totales": round(v["abonos"], 2),
            "saldo_pendiente": round(v["compras"] + v["comision"] - v["abonos"], 2),
        }
        for mon, v in sorted(por_moneda.items())
    ]

    return {
        "cliente_id": cliente.id,
        "nombre": cliente.nombre,
        "nit": cliente.nit,
        "empresa": cliente.empresa,
        "totales_por_moneda": totales_por_moneda,
        "fecha_ultimo_abono": fecha_ultimo_abono,
        "pedidos": pedidos,
    }
