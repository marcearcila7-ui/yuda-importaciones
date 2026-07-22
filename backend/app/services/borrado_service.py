"""Borrado de cotizaciones y clientes.

Eliminar una cotización toca muchas tablas (ítems, pedidos generados, lotes de
OCR, seguimiento, avisos) y además deja archivos en el storage. Está aquí, en un
solo sitio, porque se usa desde dos lados: al borrar una cotización suelta y al
borrar un cliente con todo lo suyo.

La contabilidad NO se borra en cascada: si una cotización o un cliente tiene
movimientos de cuenta (abonos, cobros), el borrado se bloquea y se avisa. Para
eso está desactivar al cliente.
"""
from sqlalchemy.orm import Session

from app.models.cuenta import MovimientoCuenta
from app.models.item import Item
from app.models.lote import LoteItem, LoteOCR
from app.models.notificacion import Notificacion
from app.models.pedido import PedidoGenerado
from app.models.seguimiento import SeguimientoPedido
from app.models.sesion import Sesion
from app.services.storage_service import borrar_archivos, ruta_desde_url


def tiene_movimientos_sesion(db: Session, sesion_id: str) -> bool:
    """¿La cotización tiene contabilidad registrada?"""
    return (
        db.query(MovimientoCuenta.id)
        .filter(MovimientoCuenta.sesion_id == sesion_id)
        .first()
        is not None
    )


def tiene_movimientos_cliente(db: Session, cliente_id: str) -> bool:
    """¿El cliente tiene abonos o cobros registrados?"""
    return (
        db.query(MovimientoCuenta.id)
        .filter(MovimientoCuenta.cliente_id == cliente_id)
        .first()
        is not None
    )


def borrar_sesiones(db: Session, sesion_ids: list[str]) -> list[tuple[str, list[str]]]:
    """Borra las cotizaciones dadas con todo lo que cuelga de ellas.

    NO hace commit: quien llama decide cuándo confirmar. Devuelve la lista de
    archivos a borrar del storage (bucket, rutas) para hacerlo DESPUÉS del
    commit, porque borrar archivos no se puede deshacer.
    """
    if not sesion_ids:
        return []

    # Archivos a limpiar: fotos de los productos, fotos de los lotes de OCR y
    # los Excel/PDF de los pedidos al proveedor.
    lote_ids = [
        lid
        for (lid,) in db.query(LoteOCR.id).filter(LoteOCR.sesion_id.in_(sesion_ids)).all()
    ]
    fotos_urls: list[str | None] = []
    for foto_url, foto_final in db.query(Item.foto_url, Item.foto_final_url).filter(
        Item.sesion_id.in_(sesion_ids)
    ):
        fotos_urls.extend([foto_url, foto_final])
    if lote_ids:
        fotos_urls.extend(
            u for (u,) in db.query(LoteItem.foto_url).filter(LoteItem.lote_id.in_(lote_ids))
        )
    pedidos_urls: list[str | None] = []
    for xlsx, pdf in db.query(
        PedidoGenerado.archivo_xlsx_url, PedidoGenerado.archivo_pdf_url
    ).filter(PedidoGenerado.sesion_id.in_(sesion_ids)):
        pedidos_urls.extend([xlsx, pdf])

    # Primero lo que depende de la cotización (FK), después la cotización.
    borrar = lambda consulta: consulta.delete(synchronize_session=False)  # noqa: E731
    borrar(db.query(Item).filter(Item.sesion_id.in_(sesion_ids)))
    borrar(db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id.in_(sesion_ids)))
    borrar(db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id.in_(sesion_ids)))
    borrar(db.query(Notificacion).filter(Notificacion.sesion_id.in_(sesion_ids)))
    if lote_ids:
        borrar(db.query(LoteItem).filter(LoteItem.lote_id.in_(lote_ids)))
        borrar(db.query(LoteOCR).filter(LoteOCR.sesion_id.in_(sesion_ids)))
    borrar(db.query(Sesion).filter(Sesion.id.in_(sesion_ids)))

    return [("fotos", fotos_urls), ("pedidos", pedidos_urls)]


def limpiar_storage(archivos: list[tuple[str, list[str]]]) -> None:
    """Borra del storage los archivos de las cotizaciones eliminadas.

    Es best-effort a propósito: si el storage falla, la cotización ya está
    borrada y no tiene sentido devolverle un error a la vendedora.
    """
    for bucket, urls in archivos:
        borrar_archivos(bucket, [ruta_desde_url(u, bucket) for u in urls])
