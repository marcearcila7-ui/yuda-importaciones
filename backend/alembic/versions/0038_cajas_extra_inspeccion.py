"""Cajas extra (medidas distintas) en la inspección de bodega

Revision ID: 0038_cajas_extra_inspeccion
Revises: 0037_bodega_asignacion
Create Date: 2026-09-21

A veces la mercancía no llega en cajas uniformes (ej. 3 cajas de 100
unidades y 1 caja de 50, o con medidas/peso distintos entre cajas). El
modelo de un solo ctns/qty_por_ctn/medidas por ítem no alcanza para eso, así
que se agrega una lista aparte de "cajas extra": cada una con sus propias
cajas, unidades por caja, medidas y peso, ADEMÁS de lo que ya haya en los
campos normales de la inspección (que siguen sirviendo para el caso
uniforme, que es el más común).
"""
from alembic import op
import sqlalchemy as sa

revision = "0038_cajas_extra_inspeccion"
down_revision = "0037_bodega_asignacion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("item_inspeccion_bodega", sa.Column("cajas_extra", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("item_inspeccion_bodega", "cajas_extra")
