"""Items: observación del cliente al aprobar el despacho

Revision ID: 0048_item_cliente_observacion
Revises: 0047_cubicaje_adjuntos
Create Date: 2026-09-25

El cliente ahora aprueba el despacho producto por producto desde su portal,
y puede dejar una observación sobre la inspección de cada uno.
"""
from alembic import op
import sqlalchemy as sa

revision = "0048_item_cliente_observacion"
down_revision = "0047_cubicaje_adjuntos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("cliente_observacion", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "cliente_observacion")
