"""Archivar cotizaciones al reactivar un cliente borrado

Revision ID: 0055_sesion_archivada
Revises: 0054_indice_vendedora_dueno
Create Date: 2026-09-28

Reactivar un cliente que había sido desactivado (borrar y volver a crear con
la misma sigla desde Yuda Contable) traía de vuelta TODO su historial de
cotizaciones -incluidas las de una gestión anterior, de otra vendedora, con
su propio chat de cubicaje- a quien fuera el dueño nuevo. Con este campo, esas
cotizaciones previas quedan archivadas (siguen existiendo, solo dejan de
aparecer en las listas activas) en vez de reaparecer mezcladas con lo nuevo.
"""
from alembic import op
import sqlalchemy as sa

revision = "0055_sesion_archivada"
down_revision = "0054_indice_vendedora_dueno"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sesiones", sa.Column("archivada_en", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("sesiones", "archivada_en")
