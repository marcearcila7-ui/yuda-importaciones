"""Revocación de sesiones: columna token_version en users y clientes

Revision ID: 0012_token_version
Revises: 0011_indices_fk
Create Date: 2026-07-18

Al subir token_version se invalidan todos los JWT emitidos antes (el token lleva
el claim 'tv' y se compara contra este valor en cada request). Se usa, por
ejemplo, al resetear la contraseña: las sesiones viejas dejan de servir.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_token_version"
down_revision = "0011_indices_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for tabla in ("users", "clientes"):
        op.add_column(
            tabla,
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    for tabla in ("users", "clientes"):
        op.drop_column(tabla, "token_version")
