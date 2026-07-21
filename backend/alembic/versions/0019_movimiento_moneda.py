"""Moneda de cobro por movimiento/pedido (USD/COP/RMB/EUR)

Revision ID: 0019_movimiento_moneda
Revises: 0018_movimiento_pedido
Create Date: 2026-07-21

La contadora elige en qué moneda se le cobra al cliente por pedido. Sin
conversión: los montos se muestran en la moneda registrada. Default USD.
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_movimiento_moneda"
down_revision = "0018_movimiento_pedido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "movimientos_cuenta",
        sa.Column("moneda", sa.String(), server_default="USD", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("movimientos_cuenta", "moneda")
