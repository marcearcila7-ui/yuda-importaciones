"""Módulo Contadora: pagos a tiendas 30/70

Revision ID: 0016_pedidos_tienda
Revises: 0015_cuentas_clientes
Create Date: 2026-07-20

Registro de pedidos a tiendas en China con su esquema de pago 30/70, comisión de
la tienda y la empleada que lo gestionó. El 30/70/comisión se calculan del total.
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_pedidos_tienda"
down_revision = "0015_cuentas_clientes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pedidos_tienda",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("nombre_tienda", sa.String(), nullable=False),
        sa.Column("fecha_pedido", sa.Date(), nullable=True),
        sa.Column("monto_total", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("fecha_pago_30", sa.Date(), nullable=True),
        sa.Column("fecha_estimada_entrega", sa.Date(), nullable=True),
        sa.Column("fecha_real_entrega", sa.Date(), nullable=True),
        sa.Column("fecha_estimada_pago_70", sa.Date(), nullable=True),
        sa.Column("fecha_pago_70", sa.Date(), nullable=True),
        sa.Column("pct_comision_tienda", sa.Float(), server_default="0", nullable=False),
        sa.Column("empleada_id", sa.String(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["empleada_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pedidos_tienda_empleada_id", "pedidos_tienda", ["empleada_id"])

    # Referencia genérica en notificaciones (para no duplicar la alerta por pedido).
    op.add_column("notificaciones", sa.Column("ref_id", sa.String(), nullable=True))
    op.create_index("ix_notificaciones_ref_id", "notificaciones", ["ref_id"])


def downgrade() -> None:
    op.drop_index("ix_notificaciones_ref_id", table_name="notificaciones")
    op.drop_column("notificaciones", "ref_id")
    op.drop_index("ix_pedidos_tienda_empleada_id", table_name="pedidos_tienda")
    op.drop_table("pedidos_tienda")
