"""Modulo de cotizacion para bolsos

Revision ID: 0026_bolsos
Revises: 0025_revertir_reset_password
Create Date: 2026-09-09

Los bolsos necesitan mas rigor que un producto generico: tamano, empaque,
etiqueta, herrajes, riata/correa, el minimo que exige la TIENDA (no el
modelo puntual, que puede ser solo cajas o cajas + piezas por caja), y
fotos aparte de la que lee el OCR (interior, herrajes, riata, exterior).

De paso, "colores" ya lo lee el OCR hoy pero nunca se guardaba en el
producto final (se perdia al agregarlo desde la revision): se agrega la
columna para toda cotizacion, no solo bolsos.
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_bolsos"
down_revision = "0025_revertir_reset_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sesiones",
        sa.Column("tipo_cotizacion", sa.String(), nullable=False, server_default="productos"),
    )
    op.add_column("items", sa.Column("colores", sa.String(), nullable=True))
    op.add_column("items", sa.Column("tamano", sa.String(), nullable=True))
    op.add_column("items", sa.Column("empaque", sa.String(), nullable=True))
    op.add_column("items", sa.Column("etiqueta", sa.String(), nullable=True))
    op.add_column("items", sa.Column("herrajes", sa.String(), nullable=True))
    op.add_column("items", sa.Column("riata", sa.String(), nullable=True))
    op.add_column("items", sa.Column("minimo_cajas_tienda", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("minimo_piezas_caja_tienda", sa.Integer(), nullable=True))
    op.add_column("items", sa.Column("fotos_extra", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "fotos_extra")
    op.drop_column("items", "minimo_piezas_caja_tienda")
    op.drop_column("items", "minimo_cajas_tienda")
    op.drop_column("items", "riata")
    op.drop_column("items", "herrajes")
    op.drop_column("items", "etiqueta")
    op.drop_column("items", "empaque")
    op.drop_column("items", "tamano")
    op.drop_column("items", "colores")
    op.drop_column("sesiones", "tipo_cotizacion")
