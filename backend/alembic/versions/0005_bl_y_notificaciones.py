"""BL en el seguimiento y avisos internos para Marcela

Revision ID: 0005_bl_y_notificaciones
Revises: 0004_portal_clientes
Create Date: 2026-06-07

"""
from alembic import op
import sqlalchemy as sa

revision = "0005_bl_y_notificaciones"
down_revision = "0004_portal_clientes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # BL (Bill of Lading): lo carga Marcela cuando el contenedor está en tránsito
    op.add_column("seguimientos", sa.Column("bl_numero", sa.String(), nullable=True))
    op.add_column("seguimientos", sa.Column("bl_pdf_url", sa.String(), nullable=True))

    # Avisos internos para el equipo (ej. "cotización lista para envío")
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("usuario_id", sa.String(), nullable=False),
        sa.Column("sesion_id", sa.String(), nullable=True),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notificaciones_usuario", "notificaciones", ["usuario_id", "leida"]
    )


def downgrade() -> None:
    op.drop_index("ix_notificaciones_usuario", table_name="notificaciones")
    op.drop_table("notificaciones")
    op.drop_column("seguimientos", "bl_pdf_url")
    op.drop_column("seguimientos", "bl_numero")
