"""Cuentas de clientes: movimientos (ledger) + NIT del cliente

Revision ID: 0015_cuentas_clientes
Revises: 0014_sesion_contenedor
Create Date: 2026-07-20

Estado de cuenta por cliente/contenedor replicando el libro de Marcela
(ENVIO/FECHA/GUIA/DESCRIPCION/VALOR/COMISIÓN YUDA/ABONO/SALDO/NOTA). El SALDO no
se almacena: es acumulado y se calcula al leer.
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_cuentas_clientes"
down_revision = "0014_sesion_contenedor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clientes", sa.Column("nit", sa.String(), nullable=True))

    op.create_table(
        "movimientos_cuenta",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("cliente_id", sa.String(), nullable=False),
        sa.Column("contenedor_id", sa.String(), nullable=True),
        sa.Column("envio", sa.String(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=True),
        sa.Column("guia", sa.String(), nullable=True),
        sa.Column("descripcion", sa.String(), nullable=True),
        sa.Column("valor_mercancia", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("comision_yuda", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("abono", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["cliente_id"], ["clientes.id"]),
        sa.ForeignKeyConstraint(["contenedor_id"], ["contenedores.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_movimientos_cuenta_cliente_id", "movimientos_cuenta", ["cliente_id"])
    op.create_index("ix_movimientos_cuenta_contenedor_id", "movimientos_cuenta", ["contenedor_id"])


def downgrade() -> None:
    op.drop_index("ix_movimientos_cuenta_contenedor_id", table_name="movimientos_cuenta")
    op.drop_index("ix_movimientos_cuenta_cliente_id", table_name="movimientos_cuenta")
    op.drop_table("movimientos_cuenta")
    op.drop_column("clientes", "nit")
