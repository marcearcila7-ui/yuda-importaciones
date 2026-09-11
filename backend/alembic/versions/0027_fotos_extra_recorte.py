"""Recorte a mano de las fotos de detalle del bolso

Revision ID: 0027_fotos_extra_recorte
Revises: 0026_bolsos
Create Date: 2026-09-11

Las 4 fotos de detalle del bolso (interior/herrajes/riata/exterior) se subian
tal cual, sin poder ajustarlas despues: si salian giradas o mal encuadradas,
la unica opcion era volver a subir la foto entera. Se agrega una columna
paralela a `fotos_extra` (mismo patron que foto_url/foto_final_url en el
producto): `fotos_extra` guarda SIEMPRE la foto original tal como se subio,
y `fotos_extra_final` guarda el resultado del recorte/giro a mano, por tipo,
cuando existe.
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_fotos_extra_recorte"
down_revision = "0026_bolsos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("items", sa.Column("fotos_extra_final", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "fotos_extra_final")
