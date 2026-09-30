"""Calendario compartido de bodega (recibe/carga)

Revision ID: 0057_calendario
Revises: 0056_devolver_no_llego
Create Date: 2026-09-30

Nueva app "Yuda Calendario": calendario libre para que admin/vendedora/bodega
registren qué se recibe y qué se carga cada día, por cliente/marca. Tiene su
propia campanita de notificaciones (calendario_notificaciones), separada de
la del cotizador y de Yuda Logistic a propósito -cada app del ecosistema
maneja las suyas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0057_calendario"
down_revision = "0056_devolver_no_llego"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "calendario_tareas",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("marca_cliente", sa.String(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("creado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("creado_por_nombre", sa.String(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actualizado_por_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actualizado_por_nombre", sa.String(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("calendario_tareas_fecha_idx", "calendario_tareas", ["fecha"])

    op.create_table(
        "calendario_notificaciones",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("usuario_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tarea_id", sa.String(), sa.ForeignKey("calendario_tareas.id"), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("calendario_notificaciones_usuario_idx", "calendario_notificaciones", ["usuario_id"])
    op.create_index("calendario_notificaciones_tarea_idx", "calendario_notificaciones", ["tarea_id"])


def downgrade() -> None:
    op.drop_table("calendario_notificaciones")
    op.drop_table("calendario_tareas")
