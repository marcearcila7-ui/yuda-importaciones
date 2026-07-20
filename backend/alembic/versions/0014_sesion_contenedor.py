"""Enlace cotización → contenedor (para tomar la TRM del embarque al facturar)

Revision ID: 0014_sesion_contenedor
Revises: 0013_contenedores
Create Date: 2026-07-20

Agrega sesiones.contenedor_id (FK nullable). Cuando está seteado, la factura en
USD usa la TRM del contenedor; si es NULL, cae a sesiones.tipo_cambio_usd.
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_sesion_contenedor"
down_revision = "0013_contenedores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sesiones",
        sa.Column("contenedor_id", sa.String(), nullable=True),
    )
    op.create_index("ix_sesiones_contenedor_id", "sesiones", ["contenedor_id"])
    op.create_foreign_key(
        "fk_sesiones_contenedor_id",
        "sesiones",
        "contenedores",
        ["contenedor_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_sesiones_contenedor_id", "sesiones", type_="foreignkey")
    op.drop_index("ix_sesiones_contenedor_id", table_name="sesiones")
    op.drop_column("sesiones", "contenedor_id")
