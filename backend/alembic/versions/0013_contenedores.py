"""Entidad Contenedor / embarque con TRM (tasa RMB→USD) manual

Revision ID: 0013_contenedores
Revises: 0012_token_version
Create Date: 2026-07-20

Agrupa cotizaciones y envíos bajo un embarque y guarda la TRM que fija la
contadora para convertir RMB a USD en facturas y cuentas de clientes.
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_contenedores"
down_revision = "0012_token_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contenedores",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("codigo", sa.String(), nullable=False),
        sa.Column("trm_usd", sa.Float(), server_default="6.7", nullable=False),
        sa.Column("fecha", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(), server_default="abierto", nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contenedores_codigo", "contenedores", ["codigo"])


def downgrade() -> None:
    op.drop_index("ix_contenedores_codigo", table_name="contenedores")
    op.drop_table("contenedores")
