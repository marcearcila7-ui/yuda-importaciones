"""Cuentas por pedido: asociar cada movimiento a una cotización (pedido)

Revision ID: 0018_movimiento_pedido
Revises: 0017_fecha_comision
Create Date: 2026-07-21

Cada movimiento de la cuenta se cuelga de un pedido (cotización) para llevar la
contabilidad por pedido y no mezclar los abonos de distintos pedidos del mismo
cliente. Nullable: los movimientos viejos quedan como "sin pedido".
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_movimiento_pedido"
down_revision = "0017_fecha_comision"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movimientos_cuenta", sa.Column("sesion_id", sa.String(), nullable=True))
    op.create_index("ix_movimientos_cuenta_sesion_id", "movimientos_cuenta", ["sesion_id"])
    op.create_foreign_key(
        "fk_movimientos_cuenta_sesion_id",
        "movimientos_cuenta",
        "sesiones",
        ["sesion_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_movimientos_cuenta_sesion_id", "movimientos_cuenta", type_="foreignkey")
    op.drop_index("ix_movimientos_cuenta_sesion_id", table_name="movimientos_cuenta")
    op.drop_column("movimientos_cuenta", "sesion_id")
