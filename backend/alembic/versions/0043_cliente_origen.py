"""Origen del cliente: manual o importado de Yuda Contable

Revision ID: 0043_cliente_origen
Revises: 0042_push_subscriptions
Create Date: 2026-09-22

Sin esto, un contacto importado en bloque de Yuda Contable (datos
mínimos, sin vendedora real asignada todavía) era indistinguible de un
cliente de verdad creado a mano -se mezclaban en la misma lista sin
ninguna forma de separarlos. Se backfillea usando el patrón de correo
que ya usaba el importador (sigla@contable.yudaimportaciones.local) para
que los ya importados antes de este cambio también queden marcados.
"""
from alembic import op
import sqlalchemy as sa

revision = "0043_cliente_origen"
down_revision = "0042_push_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("origen", sa.String(), nullable=False, server_default="manual"),
    )
    op.execute(
        "UPDATE clientes SET origen = 'importado_contable' "
        "WHERE email LIKE '%@contable.yudaimportaciones.local'"
    )


def downgrade() -> None:
    op.drop_column("clientes", "origen")
