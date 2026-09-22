"""Cliente: forzar cambio de contraseña + estado de cuenta oficial

Revision ID: 0044_cliente_pw_estado_cuenta
Revises: 0043_cliente_origen
Create Date: 2026-09-23

debe_cambiar_password: se usa en la importación masiva de Yuda Contable,
que le pone la misma clave de plantilla a todos -el portal obliga a
cambiarla antes de dejar ver nada más.

estado_cuenta_oficial_url/_actualizado_en: Marcela sube el estado de
cuenta real de Yuda Contable (PDF/imagen) para que el cliente lo vea en
su portal. Documento puntual, sin conexión en vivo entre las dos apps.
"""
from alembic import op
import sqlalchemy as sa

revision = "0044_cliente_pw_estado_cuenta"
down_revision = "0043_cliente_origen"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "clientes",
        sa.Column("debe_cambiar_password", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("clientes", sa.Column("estado_cuenta_oficial_url", sa.String(), nullable=True))
    op.add_column(
        "clientes",
        sa.Column("estado_cuenta_oficial_actualizado_en", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("clientes", "estado_cuenta_oficial_actualizado_en")
    op.drop_column("clientes", "estado_cuenta_oficial_url")
    op.drop_column("clientes", "debe_cambiar_password")
