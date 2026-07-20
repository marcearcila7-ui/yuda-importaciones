"""Cálculo del estado de cuenta de un cliente a partir de sus movimientos.

El SALDO es acumulado (no se almacena): cada movimiento suma valor + comisión y
resta el abono, arrastrando el saldo anterior. Los agregados (compras, comisión,
abonos, saldo pendiente, último abono) resumen toda la cuenta.
"""
from datetime import date

from app.models.cliente import Cliente
from app.models.cuenta import MovimientoCuenta


def _f(valor) -> float:
    """Numeric de SQLAlchemy → float (evita Decimal en las respuestas)."""
    return float(valor or 0)


def _orden(mov: MovimientoCuenta):
    """Orden cronológico estable: por fecha y, a igualdad, por creación."""
    return (mov.fecha or date.min, mov.created_at)


def construir_estado_cuenta(
    cliente: Cliente, movimientos: list[MovimientoCuenta]
) -> dict:
    """Arma el estado de cuenta: movimientos con saldo acumulado + totales."""
    ordenados = sorted(movimientos, key=_orden)

    compras = comision = abonos = 0.0
    saldo = 0.0
    fecha_ultimo_abono: date | None = None
    filas = []
    for m in ordenados:
        valor = _f(m.valor_mercancia)
        com = _f(m.comision_yuda)
        ab = _f(m.abono)
        compras += valor
        comision += com
        abonos += ab
        saldo += valor + com - ab
        if ab > 0 and (fecha_ultimo_abono is None or (m.fecha and m.fecha > fecha_ultimo_abono)):
            fecha_ultimo_abono = m.fecha
        filas.append(
            {
                "id": m.id,
                "cliente_id": m.cliente_id,
                "contenedor_id": m.contenedor_id,
                "envio": m.envio,
                "fecha": m.fecha,
                "guia": m.guia,
                "descripcion": m.descripcion,
                "valor_mercancia": round(valor, 2),
                "comision_yuda": round(com, 2),
                "abono": round(ab, 2),
                "saldo": round(saldo, 2),
                "nota": m.nota,
                "created_at": m.created_at,
            }
        )

    return {
        "cliente_id": cliente.id,
        "nombre": cliente.nombre,
        "nit": cliente.nit,
        "empresa": cliente.empresa,
        "compras_totales": round(compras, 2),
        "comision_total": round(comision, 2),
        "abonos_totales": round(abonos, 2),
        "saldo_pendiente": round(compras + comision - abonos, 2),
        "fecha_ultimo_abono": fecha_ultimo_abono,
        "movimientos": filas,
    }
