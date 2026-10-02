"""Marcar qué mensajes del chat de cubicaje los escribió el sistema

Los avisos de "no llegó" / "hay que devolver" y el reporte automático de
cubicaje se guardaban igual que un mensaje escrito a mano por bodega, así
que no había forma de distinguirlos. Hacía falta para reiniciar la revisión:
se borra lo que puso el sistema por esa revisión, y la conversación entre
bodega y la vendedora se conserva.

Revision ID: 0060_cubicaje_mensaje_automatico
Revises: 0059_creado_por_nullable
"""
import sqlalchemy as sa
from alembic import op

revision = "0060_cubicaje_mensaje_automatico"
down_revision = "0059_creado_por_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cubicaje_mensajes",
        sa.Column("automatico", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Los reportes que ya existen los generó el sistema en su totalidad (el
    # reporte a mano de bodega se manda por otro camino y queda como nota).
    op.execute("UPDATE cubicaje_mensajes SET automatico = true WHERE tipo = 'reporte'")


def downgrade() -> None:
    op.drop_column("cubicaje_mensajes", "automatico")
