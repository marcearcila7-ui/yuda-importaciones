"""El abono guarda en que moneda entro y a que tasa se convirtio

Revision ID: 0022_abono_moneda_origen
Revises: 0021_marca_shipping_mark
Create Date: 2026-09-04

En el libro de cuentas el cliente abona en dolares o USDT y la cuenta se lleva en
otra moneda: "10,000 USDT 6,65" y en la columna del abono 66,500. Hasta ahora el
sistema guardaba solo el resultado, asi que se perdia el rastro de cuanto entro de
verdad y a que tasa, y para revisarlo habia que leer la descripcion escrita a mano.

Ahora se guardan las tres cosas: el monto como entro, su moneda y la tasa. El
abono en la moneda de la cuenta sigue siendo el que manda para el saldo, y se
calcula con esos datos cuando estan.
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_abono_moneda_origen"
down_revision = "0021_marca_shipping_mark"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("movimientos_cuenta", sa.Column("monto_origen", sa.Numeric(12, 2), nullable=True))
    op.add_column("movimientos_cuenta", sa.Column("moneda_origen", sa.String(), nullable=True))
    op.add_column("movimientos_cuenta", sa.Column("tasa_cambio", sa.Numeric(12, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("movimientos_cuenta", "tasa_cambio")
    op.drop_column("movimientos_cuenta", "moneda_origen")
    op.drop_column("movimientos_cuenta", "monto_origen")
