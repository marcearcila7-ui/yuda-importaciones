"""Aplicar la misma fecha de recibo a todos los productos de una cotización de
una sola vez no debe marcarlos como "ya revisados" (actualizado_en): eso es
para cuando bodega de verdad revisa cantidades/medidas/fotos, no solo pone una
fecha. Tampoco debe pisar lo que ya se corrigió en un producto que sí se
revisó de verdad antes."""
from datetime import date

from app.models.item import Item
from app.models.item_inspeccion import ItemInspeccionBodega
from app.models.sesion import Sesion
from app.models.user import RolUsuario


def _crear_sesion_con_items(db, vendedora_id):
    sesion = Sesion(nombre_cliente="Cliente prueba", fecha=date.today(), user_id=vendedora_id)
    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    item_sin_revisar = Item(sesion_id=sesion.id, item_no="A1", descripcion_es="Producto A", orden=1)
    item_ya_revisado = Item(sesion_id=sesion.id, item_no="A2", descripcion_es="Producto B", orden=2)
    db.add(item_sin_revisar)
    db.add(item_ya_revisado)
    db.commit()
    db.refresh(item_sin_revisar)
    db.refresh(item_ya_revisado)
    return sesion, item_sin_revisar, item_ya_revisado


def test_fecha_masiva_no_marca_como_revisado(db, client, crear_usuario, token_staff):
    crear_usuario("bodega-fm@test.com", rol=RolUsuario.bodega)
    vendedora = crear_usuario("v-fm@test.com", rol=RolUsuario.vendedora)
    sesion, item_a, item_b = _crear_sesion_con_items(db, vendedora.id)

    tok = token_staff("bodega-fm@test.com")
    r = client.put(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion/fecha-recibo-masiva",
        json={"fecha_recibo": "2026-09-29"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    for item in data["items"]:
        assert item["fecha_recibo"]["corregido"] == "2026-09-29"
        assert item["actualizado_en"] is None


def test_fecha_masiva_no_pisa_revision_real_ya_hecha(db, client, crear_usuario, token_staff):
    bodega = crear_usuario("bodega-fm2@test.com", rol=RolUsuario.bodega)
    vendedora = crear_usuario("v-fm2@test.com", rol=RolUsuario.vendedora)
    sesion, item_a, item_b = _crear_sesion_con_items(db, vendedora.id)

    # item_b ya fue revisado de verdad antes (bodega guardó cajas reales).
    insp = ItemInspeccionBodega(item_id=item_b.id, ctns=7, actualizado_por_id=bodega.id)
    from datetime import datetime, timezone
    insp.actualizado_en = datetime.now(timezone.utc)
    db.add(insp)
    db.commit()

    tok = token_staff("bodega-fm2@test.com")
    r = client.put(
        f"/api/v1/bodega/pedidos/{sesion.id}/cotizacion/fecha-recibo-masiva",
        json={"fecha_recibo": "2026-09-29"},
        headers={"Authorization": f"Bearer {tok}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()

    fila_a = next(i for i in data["items"] if i["item_id"] == item_a.id)
    fila_b = next(i for i in data["items"] if i["item_id"] == item_b.id)

    assert fila_a["fecha_recibo"]["corregido"] == "2026-09-29"
    assert fila_a["actualizado_en"] is None

    assert fila_b["fecha_recibo"]["corregido"] == "2026-09-29"
    assert fila_b["cajas"]["corregido"] == 7  # no se perdió la corrección real
    assert fila_b["actualizado_en"] is not None  # sigue marcado revisado, no se borra
