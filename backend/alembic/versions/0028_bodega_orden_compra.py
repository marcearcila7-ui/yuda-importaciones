"""Rol bodega y orden de compra de la tienda

Revision ID: 0028_bodega_orden_compra
Revises: 0027_fotos_extra_recorte
Create Date: 2026-09-17

Bodega pasa a ser un rol propio (antes esa etapa la marcaba la vendedora):
recibe el pedido confirmado y la orden de compra de la tienda, los compara y
marca "en_bodega" desde Yuda Logistic. Se agrega el valor 'bodega' al enum de
roles y dos columnas en `sesiones` para la orden de compra que el cliente
adjunta al confirmar su pedido.

Nota: Postgres no permite quitar un valor de un enum en la práctica (habría
que recrear el tipo), así que el downgrade deja 'bodega' en el enum aunque
borre las columnas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0028_bodega_orden_compra"
down_revision = "0027_fotos_extra_recorte"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'bodega'")
    op.add_column("sesiones", sa.Column("orden_compra_url", sa.String(), nullable=True))
    op.add_column("sesiones", sa.Column("orden_compra_nombre", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("sesiones", "orden_compra_nombre")
    op.drop_column("sesiones", "orden_compra_url")
