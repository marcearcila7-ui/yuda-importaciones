"""Clientes compartidos entre vendedoras + bitácora de actividad

Revision ID: 0032_cliente_vendedoras
Revises: 0031_pedido_generado_items
Create Date: 2026-09-19

Hasta ahora un cliente tenía una sola vendedora dueña (Cliente.vendedora_id).
Marcela puede asignar vendedoras ADICIONALES a un cliente (cliente_vendedoras);
la dueña original no se toca acá. Además se agrega una bitácora libre
(cliente_actividad) donde cualquiera con acceso al cliente deja notas, para
que cuando el cliente sea compartido quede registro de qué hizo cada quien.
"""
from alembic import op
import sqlalchemy as sa

revision = "0032_cliente_vendedoras"
down_revision = "0031_pedido_generado_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cliente_vendedoras",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cliente_id", sa.String(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("vendedora_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("asignado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cliente_id", "vendedora_id", name="uq_cliente_vendedora"),
    )
    op.create_index("ix_cliente_vendedoras_cliente_id", "cliente_vendedoras", ["cliente_id"])
    op.create_index("ix_cliente_vendedoras_vendedora_id", "cliente_vendedoras", ["vendedora_id"])

    op.create_table(
        "cliente_actividad",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cliente_id", sa.String(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("usuario_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("nota", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cliente_actividad_cliente_id", "cliente_actividad", ["cliente_id"])


def downgrade() -> None:
    op.drop_index("ix_cliente_actividad_cliente_id", table_name="cliente_actividad")
    op.drop_table("cliente_actividad")

    op.drop_index("ix_cliente_vendedoras_vendedora_id", table_name="cliente_vendedoras")
    op.drop_index("ix_cliente_vendedoras_cliente_id", table_name="cliente_vendedoras")
    op.drop_table("cliente_vendedoras")
