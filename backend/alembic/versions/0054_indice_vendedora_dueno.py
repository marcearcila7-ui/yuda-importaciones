"""Índice en clientes.vendedora_id

Revision ID: 0054_indice_vendedora_dueno
Revises: 0053_generado_por
Create Date: 2026-09-27

Cada listado y cada chequeo de permisos de una vendedora filtra clientes por
esta columna (listar_clientes, listar_sesiones, bodega_resumen,
_cliente_autorizado...). Sin índice era un recorrido completo de la tabla en
cada request; se nota a medida que crece la cantidad de clientes (portal de
clientes, muchos usuarios).
"""
from alembic import op

revision = "0054_indice_vendedora_dueno"
down_revision = "0053_generado_por"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_clientes_vendedora_id", "clientes", ["vendedora_id"])


def downgrade() -> None:
    op.drop_index("ix_clientes_vendedora_id", table_name="clientes")
