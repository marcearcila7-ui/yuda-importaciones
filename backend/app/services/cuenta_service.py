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
    tot_compras = tot_comision = tot_abonos = 0.0
    fecha_ultimo_abono: date | None = None

    for sid in orden_sids:
        movs = sorted(grupos[sid], key=_orden)
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

        s = ses_map.get(sid) if sid else None
        pedidos.append(
            {
                "sesion_id": sid,
                "pedido_numero": numero_pedido(s) if s else None,
                "pedido_fecha": s.fecha if s else None,
                # "Ya es pedido" cuando la cotización entró al circuito de pedido
                # (el cliente envió/confirmó cantidades → tiene packing list).
                "es_pedido": bool(s and s.pedido_estado),
                "compras_totales": round(compras, 2),
                "comision_total": round(comision, 2),
                "abonos_totales": round(abonos, 2),
                "saldo_pendiente": round(compras + comision - abonos, 2),
                "movimientos": filas,
            }
        )
        tot_compras += compras
        tot_comision += comision
        tot_abonos += abonos

    return {
        "cliente_id": cliente.id,
        "nombre": cliente.nombre,
        "nit": cliente.nit,
        "empresa": cliente.empresa,
        "compras_totales": round(tot_compras, 2),
        "comision_total": round(tot_comision, 2),
        "abonos_totales": round(tot_abonos, 2),
        "saldo_pendiente": round(tot_compras + tot_comision - tot_abonos, 2),
        "fecha_ultimo_abono": fecha_ultimo_abono,
        "pedidos": pedidos,
    }
