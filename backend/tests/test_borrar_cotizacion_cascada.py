"""Borrar una cotización de verdad, con todo lo que una cotización real
arrastra: las fotos del lote de OCR con el que se armó y el chat de cubicaje
que alguien abrió. Las dos cosas apuntan a la cotización (o a sus ítems) y, si
no se borran en el orden correcto, la base rechaza el borrado y en pantalla
solo se ve "no se pudo eliminar".
"""
from app.models.cubicaje import CubicajeVisto
from app.models.item import Item
from app.models.lote import LoteItem, LoteOCR
from app.models.sesion import Sesion
from app.models.user import RolUsuario


def test_borrar_cotizacion_armada_con_ocr_y_chat_abierto(
    client, crear_usuario, crear_cliente, crear_sesion, token_staff, db
):
    vendedora = crear_usuario("borrar1@test.com", rol=RolUsuario.vendedora)
    cliente = crear_cliente("clienteborrar1@test.com", vendedora.id)
    sesion = crear_sesion(vendedora.id, cliente.id, con_item=True)
    sesion_id = sesion.id
    item = db.query(Item).filter(Item.sesion_id == sesion.id).first()

    # Así queda una cotización armada con carga masiva: la foto del lote
    # apunta al ítem que se creó a partir de ella.
    lote = LoteOCR(sesion_id=sesion.id, estado="completado")
    db.add(lote)
    db.commit()
    db.add(LoteItem(lote_id=lote.id, foto_url="https://x/f.jpg", estado="ok", item_id=item.id))
    # Y así queda cuando alguien abrió el chat de cubicaje de esa cotización.
    db.add(CubicajeVisto(sesion_id=sesion.id, usuario_id=vendedora.id))
    db.commit()

    token = token_staff("borrar1@test.com")
    r = client.delete(f"/api/v1/sesiones/{sesion.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text

    db.expire_all()
    assert db.query(Sesion).filter(Sesion.id == sesion_id).first() is None
    assert db.query(Item).filter(Item.sesion_id == sesion_id).count() == 0
    assert db.query(LoteOCR).filter(LoteOCR.sesion_id == sesion_id).count() == 0
    assert db.query(CubicajeVisto).filter(CubicajeVisto.sesion_id == sesion_id).count() == 0
