"""Permitir creado_por_id nulo en calendario_tareas y pagos_tareas

Revision ID: 0059_creado_por_nullable
Revises: 0058_calendario_pagos
Create Date: 2026-10-01

Eliminar un usuario fallaba con un error de llave foránea si ese usuario
había creado alguna tarea de calendario o de pagos (creado_por_id era
NOT NULL). El nombre de quien creó/editó ya queda guardado aparte como texto
(creado_por_nombre/actualizado_por_nombre, que nunca cambian), así que el id
se puede dejar en null sin perder esa información visible -son tableros
compartidos, no "de un dueño", igual que ya pasa con la asignación de bodega
en seguimiento de pedidos.
"""
from alembic import op
import sqlalchemy as sa

revision = "0059_creado_por_nullable"
down_revision = "0058_calendario_pagos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("calendario_tareas", "creado_por_id", nullable=True)
    op.alter_column("pagos_tareas", "creado_por_id", nullable=True)


def downgrade() -> None:
    op.alter_column("pagos_tareas", "creado_por_id", nullable=False)
    op.alter_column("calendario_tareas", "creado_por_id", nullable=False)
