"""portal de clientes: clientes, seguimientos y vínculo en sesiones

Revision ID: 0004_portal_clientes
Revises: 0003_lotes
Create Date: 2026-06-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0004_portal_clientes"
down_revision = "0003_lotes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabla de clientes (acceso al portal)
    op.create_table(
        "clientes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("empresa", sa.String(), nullable=True),
        sa.Column("telefono", sa.String(), nullable=True),
        sa.Column("pais", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("vendedora_id", sa.String(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["vendedora_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clientes_email", "clientes", ["email"], unique=True)

    # Vínculo de la sesión con un cliente del portal
    op.add_column("sesiones", sa.Column("cliente_id", sa.String(), nullable=True))
    op.add_column(
        "sesiones",
        sa.Column(
            "enviada_cliente", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "sesiones", sa.Column("fecha_envio_cliente", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_sesiones_cliente", "sesiones", "clientes", ["cliente_id"], ["id"]
    )

    # Seguimiento del envío (1 a 1 con la sesión)
    op.create_table(
        "seguimientos",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sesion_id", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("novedades", sa.Text(), nullable=True),
        sa.Column("numero_tracking", sa.String(), nullable=True),
        sa.Column("naviera", sa.String(), nullable=True),
        sa.Column("url_tracking", sa.String(), nullable=True),
        sa.Column("fecha_eta", sa.Date(), nullable=True),
        sa.Column("hitos", sa.JSON(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sesion_id"),
    )


def downgrade() -> None:
    op.drop_table("seguimientos")
    op.drop_constraint("fk_sesiones_cliente", "sesiones", type_="foreignkey")
    op.drop_column("sesiones", "fecha_envio_cliente")
    op.drop_column("sesiones", "enviada_cliente")
    op.drop_column("sesiones", "cliente_id")
    op.drop_index("ix_clientes_email", table_name="clientes")
    op.drop_table("clientes")
