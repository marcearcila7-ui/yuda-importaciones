"""Revertir recuperar contraseña por correo

Revision ID: 0025_revertir_reset_password
Revises: 0024_reset_password
Create Date: 2026-09-09

Se descartó el flujo de recuperación por correo (Marcela no tiene forma de
generar la contraseña de aplicación de Gmail desde China sin VPN, y no
quiere depender de otro proveedor por ahora). En su lugar, el login solo
indica que se le pida el cambio de clave a la administradora. Se deja esta
migración en vez de borrar la 0024 porque esa ya corrió en producción.
"""
from alembic import op

revision = "0025_revertir_reset_password"
down_revision = "0024_reset_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("users", "reset_token_expira")
    op.drop_column("users", "reset_token_hash")


def downgrade() -> None:
    import sqlalchemy as sa

    op.add_column("users", sa.Column("reset_token_hash", sa.String(), nullable=True))
    op.add_column("users", sa.Column("reset_token_expira", sa.DateTime(timezone=True), nullable=True))
