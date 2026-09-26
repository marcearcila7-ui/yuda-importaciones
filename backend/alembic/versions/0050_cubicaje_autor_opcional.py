"""Cubicaje mensajes: autor opcional (mensajes generados por el sistema/cliente)

Revision ID: 0050_cubicaje_autor_opcional
Revises: 0049_sin_cajas_extra
Create Date: 2026-09-26

Cuando el cliente aprueba el despacho desde su portal, ese hito se dejaba
solo en un log interno (`seguimientos.avisos`) y una notificación de la
campanita, pero nunca en el hilo de cubicaje que bodega y la vendedora
realmente miran para conversar del pedido. El cliente no es un `User` de la
app, así que ese mensaje necesita un autor nulo.
"""
from alembic import op
import sqlalchemy as sa

revision = "0050_cubicaje_autor_opcional"
down_revision = "0049_sin_cajas_extra"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("cubicaje_mensajes", "autor_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("cubicaje_mensajes", "autor_id", existing_type=sa.String(), nullable=False)
