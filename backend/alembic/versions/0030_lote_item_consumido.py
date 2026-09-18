"""Marcar en lote_items cuál ya se agregó como ítem real

Revision ID: 0030_lote_item_consumido
Revises: 0029_aprobacion_cliente_despacho
Create Date: 2026-09-18

Bug: al retomar un lote de carga masiva interrumpido (recarga del navegador,
caída del servidor a mitad de revisión), el resultado de OCR ya agregado al
packing list volvía a aparecer en la lista para revisar. Si la vendedora
apretaba "Agregar buenos" de nuevo, el producto quedaba duplicado en la
cotización que ve el cliente. `lote_items.item_id` deja registrado el ítem al
que ya se convirtió cada resultado, para excluirlo al retomar.
"""
from alembic import op
import sqlalchemy as sa

revision = "0030_lote_item_consumido"
down_revision = "0029_aprobacion_cliente_despacho"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lote_items", sa.Column("item_id", sa.String(), nullable=True))
    op.create_index("ix_lote_items_item_id", "lote_items", ["item_id"])
    op.create_foreign_key(
        "fk_lote_items_item_id", "lote_items", "items", ["item_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk_lote_items_item_id", "lote_items", type_="foreignkey")
    op.drop_index("ix_lote_items_item_id", table_name="lote_items")
    op.drop_column("lote_items", "item_id")
