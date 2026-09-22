"""Archivar un pedido de la cola de bodega

Revision ID: 0039_bodega_archivado
Revises: 0038_cajas_extra_inspeccion
Create Date: 2026-09-22

Bodega puede sacar un pedido de su propia cola (ej. ya está completado hace
rato) sin borrar nada del sistema: solo deja de aparecer en sus 4 pestañas
(Sin asignar / Asignados / Pendiente cliente / Completados), para que la
lista no se llene de trabajo ya resuelto.
"""
from alembic import op
import sqlalchemy as sa

revision = "0039_bodega_archivado"
down_revision = "0038_cajas_extra_inspeccion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seguimientos", sa.Column("bodega_archivado_en", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("seguimientos", "bodega_archivado_en")
