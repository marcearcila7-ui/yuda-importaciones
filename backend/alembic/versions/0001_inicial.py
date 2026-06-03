"""migración inicial: tablas users, sesiones, items, pedidos_generados

Revision ID: 0001_inicial
Revises:
Create Date: 2026-06-02

"""
from alembic import op
import sqlalchemy as sa

# Identificadores de la revisión usados por Alembic
revision = "0001_inicial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabla de usuarios
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column(
            "rol",
            sa.Enum("admin", "vendedora", "contadora", name="rolusuario"),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Tabla de sesiones de cotización
    op.create_table(
        "sesiones",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("nombre_cliente", sa.String(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo_cambio_usd", sa.Float(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Tabla de ítems (productos)
    op.create_table(
        "items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sesion_id", sa.String(), nullable=False),
        sa.Column("supplier_nombre", sa.String(), nullable=True),
        sa.Column("supplier_numero", sa.String(), nullable=True),
        sa.Column("foto_url", sa.String(), nullable=True),
        sa.Column("item_no", sa.String(), nullable=True),
        sa.Column("descripcion_es", sa.String(), nullable=True),
        sa.Column("descripcion_en", sa.String(), nullable=True),
        sa.Column("descripcion_zh", sa.String(), nullable=True),
        sa.Column("material", sa.String(), nullable=True),
        sa.Column("uso", sa.String(), nullable=True),
        sa.Column("qty_por_ctn", sa.Integer(), nullable=True),
        sa.Column("price_rmb", sa.Float(), nullable=True),
        sa.Column("gw", sa.Float(), nullable=True),
        sa.Column("largo_cm", sa.Float(), nullable=True),
        sa.Column("ancho_cm", sa.Float(), nullable=True),
        sa.Column("alto_cm", sa.Float(), nullable=True),
        sa.Column("ctns", sa.Integer(), nullable=True),
        sa.Column("orden", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Tabla de pedidos generados
    op.create_table(
        "pedidos_generados",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sesion_id", sa.String(), nullable=False),
        sa.Column("supplier", sa.String(), nullable=False),
        sa.Column("archivo_xlsx_url", sa.String(), nullable=False),
        sa.Column("archivo_pdf_url", sa.String(), nullable=True),
        sa.Column(
            "fecha_generacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("pedidos_generados")
    op.drop_table("items")
    op.drop_table("sesiones")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    sa.Enum(name="rolusuario").drop(op.get_bind(), checkfirst=True)
