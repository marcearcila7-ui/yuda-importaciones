"""Referencia de catálogo por ítem (la que ve el cliente en la cotización)

Revision ID: 0020_item_referencia
Revises: 0019_movimiento_moneda
Create Date: 2026-07-22

Cada producto lleva una referencia al azar tipo REF-748213 que solo aparece en
los documentos del cliente. A los ítems que ya existen se les asigna una aquí
mismo, para que las cotizaciones viejas también la muestren.
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_item_referencia"
down_revision = "0019_movimiento_moneda"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("referencia", sa.String(), nullable=True))
    op.create_index("ix_items_referencia", "items", ["referencia"])

    # Backfill: una referencia distinta para cada ítem existente. Se usa el
    # generador de Postgres para no traer todas las filas al proceso.
    op.execute(
        """
        UPDATE items
           SET referencia = 'REF-' || LPAD((100000 + FLOOR(RANDOM() * 900000))::int::text, 6, '0')
         WHERE referencia IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_items_referencia", table_name="items")
    op.drop_column("items", "referencia")
