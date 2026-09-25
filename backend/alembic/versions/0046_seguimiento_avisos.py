"""Seguimiento: log de avisos automáticos que no son un cambio de etapa

Revision ID: 0046_seguimiento_avisos
Revises: 0045_cliente_contacto_real
Create Date: 2026-09-25

`hitos` guarda un registro por cada uno de los 7 estados fijos del envío, y
`actualizar_seguimiento` lo reconstruye por completo en cada guardado (borra
cualquier clave que no sea un estado válido) -no es un lugar seguro para
anotar avisos que no son un cambio de etapa, como la fecha tentativa de una
tienda puntual. `avisos` es una columna aparte, de solo anexar, para que la
vendedora vea en el historial cada vez que salió una notificación automática
al cliente, con su fecha y hora reales.
"""
from alembic import op
import sqlalchemy as sa

revision = "0046_seguimiento_avisos"
down_revision = "0045_cliente_contacto_real"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seguimientos", sa.Column("avisos", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("seguimientos", "avisos")
