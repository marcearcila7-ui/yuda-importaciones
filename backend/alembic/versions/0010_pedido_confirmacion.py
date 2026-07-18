"""Circuito de confirmación del pedido del cliente: estado + confirmado_at

Revision ID: 0010_pedido_confirmacion
Revises: 0009_ventas
Create Date: 2026-07-17

"""
from alembic import op
import sqlalchemy as sa

revision = "0010_pedido_confirmacion"
down_revision = "0009_ventas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Estado del pedido: recibido / por_confirmar / confirmado
    op.add_column("sesiones", sa.Column("pedido_estado", sa.String(), nullable=True))
    op.add_column(
        "sesiones",
        sa.Column("pedido_confirmado_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Los pedidos ya recibidos de antes quedan en estado "recibido".
    op.execute(
        "UPDATE sesiones SET pedido_estado = 'recibido' "
        "WHERE pedido_recibido_at IS NOT NULL AND pedido_estado IS NULL"
    )


def downgrade() -> None:
    op.drop_column("sesiones", "pedido_confirmado_at")
    op.drop_column("sesiones", "pedido_estado")
