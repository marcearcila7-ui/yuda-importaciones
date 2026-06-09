"""CBM directo de etiqueta y MQT (mínimo de cajas del proveedor) en los ítems

Revision ID: 0006_cbm_moq
Revises: 0005_bl_y_notificaciones
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0006_cbm_moq"
down_revision = "0005_bl_y_notificaciones"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CBM leído directo de la etiqueta (si no, se calcula por dimensiones)
    op.add_column("items", sa.Column("cbm", sa.Float(), nullable=True))
    # MQT: mínima cantidad de CAJAS que exige el proveedor
    op.add_column("items", sa.Column("moq_cajas", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "moq_cajas")
    op.drop_column("items", "cbm")
