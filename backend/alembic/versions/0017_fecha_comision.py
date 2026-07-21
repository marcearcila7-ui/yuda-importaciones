"""Comisiones de tiendas: fecha de recibo (para totalizar por período)

Revision ID: 0017_fecha_comision
Revises: 0016_pedidos_tienda
Create Date: 2026-07-20
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_fecha_comision"
down_revision = "0016_pedidos_tienda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedidos_tienda", sa.Column("fecha_comision", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("pedidos_tienda", "fecha_comision")
