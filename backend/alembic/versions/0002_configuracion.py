"""tabla configuracion (clave-valor)

Revision ID: 0002_configuracion
Revises: 0001_inicial
Create Date: 2026-06-03

"""
from alembic import op
import sqlalchemy as sa

# Identificadores de la revisión
revision = "0002_configuracion"
down_revision = "0001_inicial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracion",
        sa.Column("clave", sa.String(), nullable=False),
        sa.Column("valor", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("clave"),
    )


def downgrade() -> None:
    op.drop_table("configuracion")
