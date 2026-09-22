"""Hilo de cubicaje por pedido

Revision ID: 0040_cubicaje_mensajes
Revises: 0039_bodega_archivado
Create Date: 2026-09-22

Tabla cubicaje_mensajes: el control de cubicaje de un pedido frente al rango
de un contenedor (68-72 m3). Guarda tanto los reportes que bodega calcula y
envía a la vendedora (cuánto cubicaje dio, si sobra o falta espacio) como la
conversación alrededor (notas de bodega, respuestas de la vendedora), todo en
una sola línea de tiempo por sesión.
"""
from alembic import op
import sqlalchemy as sa

revision = "0040_cubicaje_mensajes"
down_revision = "0039_bodega_archivado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cubicaje_mensajes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("sesion_id", sa.String(), sa.ForeignKey("sesiones.id"), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("autor_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("cbm_calculado", sa.Float(), nullable=True),
        sa.Column("resultado", sa.String(), nullable=True),
        sa.Column("referencia", sa.String(), nullable=True),
        sa.Column("cajas_afectadas", sa.Integer(), nullable=True),
        sa.Column("espacio_restante_cbm", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cubicaje_mensajes_sesion_id", "cubicaje_mensajes", ["sesion_id"])


def downgrade() -> None:
    op.drop_index("ix_cubicaje_mensajes_sesion_id", table_name="cubicaje_mensajes")
    op.drop_table("cubicaje_mensajes")
