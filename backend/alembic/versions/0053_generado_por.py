"""Pedidos generados: quién le dio "Generar pedido a la tienda"

Revision ID: 0053_generado_por
Revises: 0052_cubicaje_vistos
Create Date: 2026-09-26

Marcela, como super admin, necesita ver quién de su equipo hizo cada paso
operativo de un cliente (quién avisó a bodega, quién generó la orden, quién
inspeccionó), no solo que "ya se hizo".
"""
from alembic import op
import sqlalchemy as sa

revision = "0053_generado_por"
down_revision = "0052_cubicaje_vistos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pedidos_generados",
        sa.Column("generado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pedidos_generados", "generado_por_id")
