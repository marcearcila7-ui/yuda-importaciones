"""Marca, fecha de recibo y shipping mark, para completar el formato del cliente

Revision ID: 0021_marca_shipping_mark
Revises: 0020_item_referencia
Create Date: 2026-09-04

La cotizacion del cliente tiene que traer las mismas columnas que el formato con
el que trabaja la agencia (LOGICOMEX). Faltaban tres datos que el sistema no
guardaba en ningun lado:

- marca (MARCA/BRAND) y fecha de recibo, por producto: los llena la vendedora,
  la fecha recien cuando el proveedor entrega la mercancia.
- shipping mark, por cotizacion: identifica la carga del cliente en el
  contenedor, asi que es el mismo para todos los productos del embarque.

Nacen vacios a proposito: el OCR no los puede sacar del cartel.
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_marca_shipping_mark"
down_revision = "0020_item_referencia"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("marca", sa.String(), nullable=True))
    op.add_column("items", sa.Column("fecha_recibo", sa.String(), nullable=True))
    op.add_column("sesiones", sa.Column("shipping_mark", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("sesiones", "shipping_mark")
    op.drop_column("items", "fecha_recibo")
    op.drop_column("items", "marca")
