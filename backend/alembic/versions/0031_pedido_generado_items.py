"""Líneas de pedido generado (pedida vs. real) + versión CSV/real de los archivos

Revision ID: 0031_pedido_generado_items
Revises: 0030_lote_item_consumido
Create Date: 2026-09-18

Fase A del proceso real de la bodega: cuando bodega recibe la mercancía,
compara contra el pedido que la vendedora le mandó al proveedor (agrupado por
tienda) y corrige las cantidades si algo no llegó como se pidió. Antes,
`pedidos_generados` era solo un archivo (una foto del momento de generar);
ahora guarda también las líneas (`pedido_generado_items`) con cantidad pedida
y cantidad real, y columnas para la segunda versión de los archivos (la
"real") que se regenera cuando bodega guarda su revisión. También se agrega
CSV como formato de descarga, junto a Excel y PDF.
"""
from alembic import op
import sqlalchemy as sa

revision = "0031_pedido_generado_items"
down_revision = "0030_lote_item_consumido"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedidos_generados", sa.Column("archivo_csv_url", sa.String(), nullable=True))
    op.add_column("pedidos_generados", sa.Column("archivo_real_xlsx_url", sa.String(), nullable=True))
    op.add_column("pedidos_generados", sa.Column("archivo_real_pdf_url", sa.String(), nullable=True))
    op.add_column("pedidos_generados", sa.Column("archivo_real_csv_url", sa.String(), nullable=True))
    op.add_column(
        "pedidos_generados", sa.Column("revisado_en_bodega_at", sa.DateTime(timezone=True), nullable=True)
    )

    op.create_table(
        "pedido_generado_items",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "pedido_generado_id",
            sa.String(),
            sa.ForeignKey("pedidos_generados.id"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(), sa.ForeignKey("items.id"), nullable=False),
        sa.Column("cantidad_pedida", sa.Integer(), nullable=False),
        sa.Column("cantidad_recibida", sa.Integer(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_pedido_generado_items_pedido_generado_id",
        "pedido_generado_items",
        ["pedido_generado_id"],
    )
    op.create_index("ix_pedido_generado_items_item_id", "pedido_generado_items", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_pedido_generado_items_item_id", table_name="pedido_generado_items")
    op.drop_index("ix_pedido_generado_items_pedido_generado_id", table_name="pedido_generado_items")
    op.drop_table("pedido_generado_items")

    op.drop_column("pedidos_generados", "revisado_en_bodega_at")
    op.drop_column("pedidos_generados", "archivo_real_csv_url")
    op.drop_column("pedidos_generados", "archivo_real_pdf_url")
    op.drop_column("pedidos_generados", "archivo_real_xlsx_url")
    op.drop_column("pedidos_generados", "archivo_csv_url")
