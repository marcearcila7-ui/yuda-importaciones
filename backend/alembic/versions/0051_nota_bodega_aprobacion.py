"""Seguimientos: separar la nota de bodega al aprobar de las novedades de la vendedora

Revision ID: 0051_nota_bodega_aprobacion
Revises: 0050_cubicaje_autor_opcional
Create Date: 2026-09-26

Antes compartían la misma columna (`novedades`): bodega, al marcar
"en_bodega", pisaba sin avisar lo que la vendedora/Marcela veía en su
editor de Seguimiento -aparecía un texto que ella no había escrito.
"""
from alembic import op
import sqlalchemy as sa

revision = "0051_nota_bodega_aprobacion"
down_revision = "0050_cubicaje_autor_opcional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seguimientos", sa.Column("nota_bodega_aprobacion", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("seguimientos", "nota_bodega_aprobacion")
