"""Rellena pedido_generado_items para las órdenes generadas antes de la Fase A

Revision ID: 0034_backfill_pedido_items
Revises: 0033_cliente_sigla
Create Date: 2026-09-18

Antes de la Fase A (migración 0031), `pedidos_generados` era solo el archivo:
no tenía líneas por producto. Los pedidos generados ANTES de esa migración se
quedaron sin filas en `pedido_generado_items`, así que bodega los ve sin
productos que contar y no puede guardar nada. Esta migración reconstruye esas
líneas a partir de los ítems actuales de cada sesión, agrupando por proveedor
igual que `agrupar_items_por_supplier` (nombre_numero), y usa la cantidad que
pidió el cliente si existe, o si no las cajas internas (ctns).

No toca los pedidos que ya tienen sus líneas (los generados después de la
Fase A): es puramente aditiva.
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0034_backfill_pedido_items"
down_revision = "0033_cliente_sigla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    pedidos_sin_items = conn.execute(
        sa.text(
            """
            select pg.id, pg.sesion_id, pg.supplier
            from pedidos_generados pg
            where not exists (
                select 1 from pedido_generado_items pgi
                where pgi.pedido_generado_id = pg.id
            )
            """
        )
    ).fetchall()

    for pedido_id, sesion_id, supplier in pedidos_sin_items:
        items = conn.execute(
            sa.text(
                """
                select id, ctns, cantidad_solicitada,
                       coalesce(supplier_nombre, 'Sin_Proveedor') as nombre,
                       coalesce(supplier_numero, 'SN') as numero
                from items
                where sesion_id = :sesion_id
                """
            ),
            {"sesion_id": sesion_id},
        ).fetchall()

        for item in items:
            clave = f"{item.nombre}_{item.numero}"
            if clave != supplier:
                continue
            cantidad = item.cantidad_solicitada if (item.cantidad_solicitada or 0) > 0 else item.ctns
            if not cantidad or cantidad <= 0:
                continue
            conn.execute(
                sa.text(
                    """
                    insert into pedido_generado_items
                        (id, pedido_generado_id, item_id, cantidad_pedida, cantidad_recibida, nota, created_at)
                    values
                        (:id, :pedido_generado_id, :item_id, :cantidad, null, null, now())
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "pedido_generado_id": pedido_id,
                    "item_id": item.id,
                    "cantidad": int(cantidad),
                },
            )


def downgrade() -> None:
    # No hay forma segura de distinguir las líneas rellenadas acá de las que
    # ya se hayan guardado normalmente después; no se revierte.
    pass
