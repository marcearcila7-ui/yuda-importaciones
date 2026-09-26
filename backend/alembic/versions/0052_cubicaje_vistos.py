"""Cubicaje: quién está viendo el chat ahora mismo (para no duplicar el push)

Revision ID: 0052_cubicaje_vistos
Revises: 0051_nota_bodega_aprobacion
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = "0052_cubicaje_vistos"
down_revision = "0051_nota_bodega_aprobacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cubicaje_vistos",
        sa.Column("sesion_id", sa.String(), sa.ForeignKey("sesiones.id"), primary_key=True),
        sa.Column("usuario_id", sa.String(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("visto_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cubicaje_vistos")
