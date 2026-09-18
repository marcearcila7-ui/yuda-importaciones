"""Aprobación del cliente para despachar (con plazo)

Revision ID: 0029_aprobacion_cliente_despacho
Revises: 0028_bodega_orden_compra
Create Date: 2026-09-17

Bodega recibe la mercancía de la tienda (un tercero sin cuenta en el sistema),
la inspecciona y marca "en_bodega". A partir de ahí el cliente (el dueño de la
cotización, en su portal) tiene un plazo para aprobar el despacho antes de que
Marcela lo mande por barco. Si el plazo vence sin aprobación, el despacho sigue
igual: el cliente ya no puede aprobar ni objetar pasado ese momento.
"""
from alembic import op
import sqlalchemy as sa

revision = "0029_aprobacion_cliente_despacho"
down_revision = "0028_bodega_orden_compra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "seguimientos", sa.Column("cliente_aprobo_despacho_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "seguimientos", sa.Column("aprobacion_limite_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("seguimientos", "aprobacion_limite_at")
    op.drop_column("seguimientos", "cliente_aprobo_despacho_at")
