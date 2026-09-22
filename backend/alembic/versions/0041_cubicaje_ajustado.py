"""Cubicaje ajustado a mano por bodega

Revision ID: 0041_cubicaje_ajustado
Revises: 0040_cubicaje_mensajes
Create Date: 2026-09-22

El cbm_calculado lo sigue calculando siempre el servidor (nunca se
sobreescribe: es la referencia de verdad). Este campo aparte es lo que
bodega corrige a mano cuando cree que el cálculo automático no refleja lo
que de verdad va a ocupar el pedido (ej. una medida que no quedó bien
registrada) -queda guardado junto al calculado, no en su lugar, para que
la vendedora vea ambos.
"""
from alembic import op
import sqlalchemy as sa

revision = "0041_cubicaje_ajustado"
down_revision = "0040_cubicaje_mensajes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cubicaje_mensajes", sa.Column("cbm_ajustado", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("cubicaje_mensajes", "cbm_ajustado")
