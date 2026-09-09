"""Recuperar contraseña por correo

Revision ID: 0024_reset_password
Revises: 0023_sellar_despachado_at
Create Date: 2026-09-09

Las vendedoras no tenían forma de recuperar su contraseña si la olvidaban:
tenían que buscar al programador, cuando Marcela ya podía cambiársela desde
Administración pero ellas no lo sabían. Se agrega un flujo real de "olvidé
mi contraseña" con enlace por correo. Se guarda el HASH del token (no el
token en texto plano), mismo criterio que ya se usa para las contraseñas.
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_reset_password"
down_revision = "0023_sellar_despachado_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reset_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("reset_token_expira", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "reset_token_expira")
    op.drop_column("users", "reset_token_hash")
