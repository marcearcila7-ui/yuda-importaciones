"""Pedido del cliente desde el portal: cantidades solicitadas + notas

Revision ID: 0008_pedido_cliente
Revises: 0007_foto_final
Create Date: 2026-07-16

"""
from alembic import op
import sqlalchemy as sa

revision = "0008_pedido_cliente"
down_revision = "0007_foto_final"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Cajas (CTNS) que el cliente pide desde su portal, por producto.
    op.add_column("items", sa.Column("cantidad_solicitada", sa.Integer(), nullable=True))
    # Notas del cliente y sello de cuándo envió su pedido.
    op.add_column("sesiones", sa.Column("notas_cliente", sa.Text(), nullable=True))
    op.add_column(
        "sesiones",
        sa.Column("pedido_recibido_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sesiones", "pedido_recibido_at")
    op.drop_column("sesiones", "notas_cliente")
    op.drop_column("items", "cantidad_solicitada")
