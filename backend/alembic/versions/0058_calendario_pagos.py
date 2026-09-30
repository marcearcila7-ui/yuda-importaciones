"""Calendario de pagos del área contable

Revision ID: 0058_calendario_pagos
Revises: 0057_calendario
Create Date: 2026-09-30

Nueva app "Yuda Pagos": calendario de tareas de pago (a tiendas/proveedores)
para admin/contadora. A diferencia del calendario de bodega, las tareas son
casillas fijas (tienda, cliente, monto en RMB, estatus), no texto libre, y
se pueden mover de día (una edición más, ver PUT /calendario-pagos/pagos/{id}).
Sin campanita propia: esta app no necesita notificaciones.
"""
from alembic import op
import sqlalchemy as sa

revision = "0058_calendario_pagos"
down_revision = "0057_calendario"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pagos_tareas",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tienda", sa.String(), nullable=False),
        sa.Column("cliente_id", sa.String(), sa.ForeignKey("clientes.id"), nullable=False),
        sa.Column("cliente_sigla", sa.String(), nullable=False),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("estatus", sa.String(), nullable=False),
        sa.Column("creado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("creado_por_nombre", sa.String(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actualizado_por_nombre", sa.String(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("pagos_tareas_fecha_idx", "pagos_tareas", ["fecha"])
    op.create_index("pagos_tareas_cliente_idx", "pagos_tareas", ["cliente_id"])


def downgrade() -> None:
    op.drop_table("pagos_tareas")
