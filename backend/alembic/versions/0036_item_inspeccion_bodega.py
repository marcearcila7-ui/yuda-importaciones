"""Inspección de bodega sobre la cotización del cliente

Revision ID: 0036_item_inspeccion_bodega
Revises: 0035_fecha_tentativa_proveedor
Create Date: 2026-09-21

Tabla aparte (item_inspeccion_bodega) para que bodega corrija cantidades,
medidas, peso, descripciones y demás campos de la cotización del cliente al
inspeccionar físicamente lo que llegó, más evidencia (fotos/video) y la
confirmación de que la referencia coincide. Es un espejo: el Item original
(el que ve el cliente en el portal) nunca se toca.

También agrega sesiones.shipping_mark_bodega: mismo patrón, para cuando
bodega necesita corregir el shipping mark que cargó la vendedora.
"""
from alembic import op
import sqlalchemy as sa

revision = "0036_item_inspeccion_bodega"
down_revision = "0035_fecha_tentativa_proveedor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sesiones", sa.Column("shipping_mark_bodega", sa.String(), nullable=True))

    op.create_table(
        "item_inspeccion_bodega",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), sa.ForeignKey("items.id"), nullable=False, unique=True),
        sa.Column("referencia", sa.String(), nullable=True),
        sa.Column("item_no", sa.String(), nullable=True),
        sa.Column("descripcion_es", sa.String(), nullable=True),
        sa.Column("descripcion_en", sa.String(), nullable=True),
        sa.Column("descripcion_zh", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("uso", sa.String(), nullable=True),
        sa.Column("marca", sa.String(), nullable=True),
        sa.Column("fecha_recibo", sa.String(), nullable=True),
        sa.Column("ctns", sa.Integer(), nullable=True),
        sa.Column("qty_por_ctn", sa.Integer(), nullable=True),
        sa.Column("price_rmb", sa.Float(), nullable=True),
        sa.Column("largo_cm", sa.Float(), nullable=True),
        sa.Column("ancho_cm", sa.Float(), nullable=True),
        sa.Column("alto_cm", sa.Float(), nullable=True),
        sa.Column("gw", sa.Float(), nullable=True),
        sa.Column("moq_cajas", sa.Integer(), nullable=True),
        sa.Column("tamano", sa.String(), nullable=True),
        sa.Column("empaque", sa.String(), nullable=True),
        sa.Column("etiqueta", sa.String(), nullable=True),
        sa.Column("herrajes", sa.String(), nullable=True),
        sa.Column("riata", sa.String(), nullable=True),
        sa.Column("minimo_cajas_tienda", sa.Integer(), nullable=True),
        sa.Column("minimo_piezas_caja_tienda", sa.Integer(), nullable=True),
        sa.Column("referencia_coincide", sa.Boolean(), nullable=True),
        sa.Column("fotos", sa.JSON(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actualizado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index(
        "ix_item_inspeccion_bodega_item_id", "item_inspeccion_bodega", ["item_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_item_inspeccion_bodega_item_id", table_name="item_inspeccion_bodega")
    op.drop_table("item_inspeccion_bodega")
    op.drop_column("sesiones", "shipping_mark_bodega")
