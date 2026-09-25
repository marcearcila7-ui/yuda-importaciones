"""Cubicaje: adjuntos (fotos, videos, archivos) en los mensajes del hilo

Revision ID: 0047_cubicaje_adjuntos
Revises: 0046_seguimiento_avisos
Create Date: 2026-09-25

Bodega y la vendedora necesitan poder mandarse fotos, videos y archivos
dentro del mismo chat de cubicaje (ej. la lista sobrante generada por el
sistema), no solo texto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0047_cubicaje_adjuntos"
down_revision = "0046_seguimiento_avisos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cubicaje_mensajes", sa.Column("adjuntos", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("cubicaje_mensajes", "adjuntos")
