"""Índices en foreign keys para acelerar listados (equipo, ventas, historial)

Revision ID: 0011_indices_fk
Revises: 0010_pedido_confirmacion
Create Date: 2026-07-18

Sin estos índices, Postgres escanea la tabla entera al filtrar por la FK
(p. ej. las cotizaciones de una vendedora, los ítems de una sesión, las
notificaciones de un usuario). Con pocos registros no se nota; a cientos de
cotizaciones, el panel de Marcela y el de equipo se arrastran. Cada índice
se crea si no existe ya, así la migración es segura de re-correr.
"""
from alembic import op

revision = "0011_indices_fk"
down_revision = "0010_pedido_confirmacion"
branch_labels = None
depends_on = None


# (tabla, columna) -> nombre del índice
_INDICES = [
    ("sesiones", "user_id", "ix_sesiones_user_id"),
    ("sesiones", "cliente_id", "ix_sesiones_cliente_id"),
    ("lotes_ocr", "sesion_id", "ix_lotes_ocr_sesion_id"),
    ("lote_items", "lote_id", "ix_lote_items_lote_id"),
    ("items", "sesion_id", "ix_items_sesion_id"),
    ("notificaciones", "usuario_id", "ix_notificaciones_usuario_id"),
    ("notificaciones", "sesion_id", "ix_notificaciones_sesion_id"),
    ("seguimientos", "despachado_at", "ix_seguimientos_despachado_at"),
]


def upgrade() -> None:
    for tabla, columna, nombre in _INDICES:
        op.execute(f'CREATE INDEX IF NOT EXISTS "{nombre}" ON "{tabla}" ("{columna}")')


def downgrade() -> None:
    for _tabla, _columna, nombre in _INDICES:
        op.execute(f'DROP INDEX IF EXISTS "{nombre}"')
