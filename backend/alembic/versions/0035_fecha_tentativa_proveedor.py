"""Fecha tentativa por proveedor, no por cotización

Revision ID: 0035_fecha_tentativa_proveedor
Revises: 0034_backfill_pedido_items
Create Date: 2026-09-19

La fecha tentativa que da el proveedor vivía en el hito "proveedor_recibio"
del seguimiento, que es UNO solo por cotización. Si el pedido se reparte
entre varios proveedores con fechas distintas, la segunda que se guardaba
pisaba la primera en silencio. Se mueve a una columna en pedidos_generados
(una por proveedor).
"""
from alembic import op
import sqlalchemy as sa

revision = "0035_fecha_tentativa_proveedor"
down_revision = "0034_backfill_pedido_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedidos_generados", sa.Column("fecha_tentativa_entrega", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("pedidos_generados", "fecha_tentativa_entrega")
