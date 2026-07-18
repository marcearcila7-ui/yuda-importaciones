"""Panel de ventas de Marcela: monto de la venta + sello de despacho

Revision ID: 0009_ventas
Revises: 0008_pedido_cliente
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0009_ventas"
down_revision = "0008_pedido_cliente"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Monto de la venta (USD) que ingresa Marcela al despachar el contenedor.
    op.add_column("seguimientos", sa.Column("monto_venta", sa.Numeric(12, 2), nullable=True))
    # Momento en que el pedido pasó a "en tránsito" (para filtrar ventas por fecha).
    op.add_column(
        "seguimientos",
        sa.Column("despachado_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("seguimientos", "despachado_at")
    op.drop_column("seguimientos", "monto_venta")
