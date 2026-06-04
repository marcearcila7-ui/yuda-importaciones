"""tablas de carga masiva (lotes_ocr, lote_items)

Revision ID: 0003_lotes
Revises: 0002_configuracion
Create Date: 2026-06-04

"""
from alembic import op
import sqlalchemy as sa

revision = "0003_lotes"
down_revision = "0002_configuracion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lotes_ocr",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("sesion_id", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["sesion_id"], ["sesiones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lote_items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("lote_id", sa.String(), nullable=False),
        sa.Column("foto_url", sa.String(), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("datos", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_ocr.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("lote_items")
    op.drop_table("lotes_ocr")
