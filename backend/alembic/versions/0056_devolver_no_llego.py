"""Casillas de bodega: devolver al proveedor / no llegó

Revision ID: 0056_devolver_no_llego
Revises: 0055_sesion_archivada
Create Date: 2026-09-29

Bodega necesita marcar, producto por producto durante la inspección, si algo
hay que devolverle al proveedor o si de plano no llegó -y que la vendedora se
entere al toque por el chat de cubicaje del pedido, sin tener que revisar la
cotización completa para notarlo.

(La revisión anterior se llamaba "0056_inspeccion_devolver_no_llego", pero
alembic_version.version_num es varchar(32) y ese nombre tiene 33 caracteres:
el primer intento de deploy falló justo al escribir la versión nueva -la
tabla real nunca llegó a cambiar porque todo corre en una misma transacción,
así que no hizo falta migración de corrección, solo acortar el nombre.)
"""
from alembic import op
import sqlalchemy as sa

revision = "0056_devolver_no_llego"
down_revision = "0055_sesion_archivada"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "item_inspeccion_bodega",
        sa.Column("debe_devolver", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "item_inspeccion_bodega",
        sa.Column("no_llego", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("item_inspeccion_bodega", "no_llego")
    op.drop_column("item_inspeccion_bodega", "debe_devolver")
