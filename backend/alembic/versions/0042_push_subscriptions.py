"""Suscripciones a notificaciones push

Revision ID: 0042_push_subscriptions
Revises: 0041_cubicaje_ajustado
Create Date: 2026-09-22

Guarda el endpoint que el navegador de cada usuario da al suscribirse a
push, para poder mandarle avisos aunque tenga la app cerrada. Un usuario
puede tener varias (celular, computador).
"""
from alembic import op
import sqlalchemy as sa

revision = "0042_push_subscriptions"
down_revision = "0041_cubicaje_ajustado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("usuario_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_push_subscriptions_usuario_id", "push_subscriptions", ["usuario_id"])
    op.create_index(
        "ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True,
        postgresql_ops={"endpoint": "text_pattern_ops"},
    )


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_usuario_id", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
