"""Asignación de pedidos entre varias personas de bodega + bitácora

Revision ID: 0037_bodega_asignacion
Revises: 0036_item_inspeccion_bodega
Create Date: 2026-09-21

Con varias personas trabajando bodega, hace falta saber quién tiene qué
pedido asignado (para no pisarse) y un registro de qué hizo cada quien.
"""
from alembic import op
import sqlalchemy as sa

revision = "0037_bodega_asignacion"
down_revision = "0036_item_inspeccion_bodega"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seguimientos", sa.Column("bodega_asignado_a_id", sa.String(), sa.ForeignKey("users.id"), nullable=True))
    op.add_column("seguimientos", sa.Column("bodega_asignado_en", sa.DateTime(timezone=True), nullable=True))
    op.add_column("seguimientos", sa.Column("bodega_asignado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=True))

    op.create_table(
        "pedido_bodega_actividad",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("sesion_id", sa.String(), sa.ForeignKey("sesiones.id"), nullable=False),
        sa.Column("usuario_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_pedido_bodega_actividad_sesion_id", "pedido_bodega_actividad", ["sesion_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_pedido_bodega_actividad_sesion_id", table_name="pedido_bodega_actividad")
    op.drop_table("pedido_bodega_actividad")
    op.drop_column("seguimientos", "bodega_asignado_por_id")
    op.drop_column("seguimientos", "bodega_asignado_en")
    op.drop_column("seguimientos", "bodega_asignado_a_id")
