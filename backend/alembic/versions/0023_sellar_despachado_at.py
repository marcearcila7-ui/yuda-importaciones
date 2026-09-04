"""Rellenar la fecha de despacho que quedo sin sellar

Revision ID: 0023_sellar_despachado_at
Revises: 0022_abono_moneda_origen
Create Date: 2026-09-04

El panel de ventas filtra los despachos por `despachado_at`. Los pedidos que
pasaron a "en transito" antes de que existiera ese sello lo tienen en null, y una
fila sin fecha queda FUERA de cualquier rango: el contenedor existe, pero no
aparece en "hoy", ni en "7 dias", ni en "30 dias". Solo se ve en "Todo", y desde
el panel eso se lee como que las ventas no funcionan.

La fecha real si esta guardada: es el sello del hito "en_transito", que se pone
cuando el pedido llega a esa etapa. De ahi se toma. Los que tampoco tengan hito
caen a la ultima actualizacion del seguimiento, que es lo mas cercano que hay.
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision = "0023_sellar_despachado_at"
down_revision = "0022_abono_moneda_origen"
branch_labels = None
depends_on = None

# Mismos estados que el panel considera despachados
DESPACHADOS = ("en_transito", "en_destino", "entregado")


def upgrade() -> None:
    conexion = op.get_bind()
    filas = conexion.execute(
        sa.text(
            "SELECT id, hitos, updated_at FROM seguimientos "
            "WHERE despachado_at IS NULL AND estado = ANY(:estados)"
        ),
        {"estados": list(DESPACHADOS)},
    ).fetchall()

    for fila in filas:
        hitos = fila.hitos or {}
        sello = None
        for estado in DESPACHADOS:
            ts = (hitos.get(estado) or {}).get("ts")
            if ts:
                try:
                    sello = datetime.fromisoformat(ts)
                    break
                except ValueError:
                    continue
        if sello is None:
            sello = fila.updated_at
        if sello is None:
            continue
        conexion.execute(
            sa.text("UPDATE seguimientos SET despachado_at = :sello WHERE id = :id"),
            {"sello": sello, "id": fila.id},
        )


def downgrade() -> None:
    # No se deshace: volver a poner null perderia la fecha recuperada.
    pass
