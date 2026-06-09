"""Foto final (limpia) del producto para los documentos de cliente y proveedor

Revision ID: 0007_foto_final
Revises: 0006_cbm_moq
Create Date: 2026-06-08

"""
from alembic import op
import sqlalchemy as sa

revision = "0007_foto_final"
down_revision = "0006_cbm_moq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Foto 2: la que va en los documentos finales (cliente/proveedor). El OCR
    # sigue usando foto_url (la del producto con datos/tablero).
    op.add_column("items", sa.Column("foto_final_url", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "foto_final_url")
