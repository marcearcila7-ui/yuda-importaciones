"""Cliente: whatsapp y correo de contacto real (separado del login del portal)

Revision ID: 0045_cliente_contacto_real
Revises: 0044_cliente_pw_estado_cuenta
Create Date: 2026-09-23

Los avisos por Brevo (aprobar despacho, pedido enviado a proveedor, etc.)
usaban `email`, que para los clientes importados de Yuda Contable es un
usuario de portal sintético (nombre@yudaimportaciones.com), no una casilla
real -los correos se iban a una dirección que no existe. email_contacto
guarda el correo real por separado; whatsapp guarda el número de WhatsApp
de Yuda Contable (puede diferir del teléfono).
"""
from alembic import op
import sqlalchemy as sa

revision = "0045_cliente_contacto_real"
down_revision = "0044_cliente_pw_estado_cuenta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("whatsapp", sa.String(), nullable=True))
    op.add_column("clientes", sa.Column("email_contacto", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("clientes", "email_contacto")
    op.drop_column("clientes", "whatsapp")
