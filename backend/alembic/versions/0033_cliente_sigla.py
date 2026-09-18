"""Sigla de Yuda Contable en el cliente (puente, sin datos financieros)

Revision ID: 0033_cliente_sigla
Revises: 0032_cliente_vendedoras
Create Date: 2026-09-19

Fase 2: cada cliente del cotizador puede guardar el código corto ("sigla")
con el que aparece en Yuda Contable (app aparte). Es solo una etiqueta de
referencia cruzada que Marcela escribe a mano; nunca se trae saldo ni
movimientos de esa app hacia acá.
"""
from alembic import op
import sqlalchemy as sa

revision = "0033_cliente_sigla"
down_revision = "0032_cliente_vendedoras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("sigla", sa.String(), nullable=True))
    op.create_unique_constraint("uq_clientes_sigla", "clientes", ["sigla"])


def downgrade() -> None:
    op.drop_constraint("uq_clientes_sigla", "clientes", type_="unique")
    op.drop_column("clientes", "sigla")
