"""Item inspeccion bodega: confirmar que no hay cajas extra que reportar

Revision ID: 0049_sin_cajas_extra
Revises: 0048_item_cliente_observacion
Create Date: 2026-09-26

Bodega puede confirmar a propósito que no llegaron cajas fuera de lo
uniforme, en vez de dejar esa sección simplemente vacía y ambigua.
"""
from alembic import op
import sqlalchemy as sa

revision = "0049_sin_cajas_extra"
down_revision = "0048_item_cliente_observacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "item_inspeccion_bodega",
        sa.Column("sin_cajas_extra", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("item_inspeccion_bodega", "sin_cajas_extra")
