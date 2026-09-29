"""No todo lo que se cotiza se termina comprando: el cliente puede quitar
productos desde su portal antes de confirmar. El dashboard debe mostrar,
aparte del valor cotizado, el valor REALMENTE pedido al proveedor (las
cantidades que quedaron en la orden generada, no las CTNS de la cotización)."""
from datetime import date, datetime, timezone

from app.models.item import Item
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.sesion import Sesion
from app.models.user import RolUsuario


def _crear_sesion_con_pedido_parcial(db, vendedora_id):
    """Una cotización de 2 productos (10 y 5 cajas), pero el cliente solo
    terminó pidiendo 10 cajas del primero -el segundo se quitó del todo desde
    el portal- así que el pedido generado a proveedor solo trae esa línea."""
    sesion = Sesion(
        nombre_cliente="Cliente prueba",
        fecha=date.today(),
        user_id=vendedora_id,
        tipo_cambio_usd=10.0,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)

    item_pedido = Item(
        sesion_id=sesion.id, supplier_nombre="Prov", descripcion_es="A",
        ctns=10, qty_por_ctn=100, price_rmb=1.0, orden=1,
    )
    item_no_pedido = Item(
        sesion_id=sesion.id, supplier_nombre="Prov", descripcion_es="B",
        ctns=5, qty_por_ctn=100, price_rmb=1.0, orden=2,
    )
    db.add(item_pedido)
    db.add(item_no_pedido)
    db.commit()
    db.refresh(item_pedido)
    db.refresh(item_no_pedido)

    pedido = PedidoGenerado(
        sesion_id=sesion.id,
        supplier="Prov_1",
        archivo_xlsx_url="https://fake/pedido.xlsx",
        fecha_generacion=datetime.now(timezone.utc),
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    # Solo el item_pedido quedó en la orden generada (10 cajas): el cliente
    # quitó item_no_pedido antes de confirmar, así que nunca entra aquí.
    db.add(
        PedidoGeneradoItem(pedido_generado_id=pedido.id, item_id=item_pedido.id, cantidad_pedida=10)
    )
    db.commit()
    return sesion


def test_metricas_reflejan_solo_lo_realmente_pedido(db, client, crear_usuario, token_staff):
    admin = crear_usuario("admin-metricas@test.com", rol=RolUsuario.admin)
    vendedora = crear_usuario("v-metricas@test.com", rol=RolUsuario.vendedora)
    _crear_sesion_con_pedido_parcial(db, vendedora.id)

    tok = token_staff("admin-metricas@test.com")
    r = client.get("/api/v1/admin/metricas", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text
    data = r.json()

    # Cotizado: 10*100*1 + 5*100*1 = 1500 RMB (los dos productos)
    assert data["total_rmb_mes"] == 1500.0
    # Realmente pedido: solo 10*100*1 = 1000 RMB (el que sí se compró)
    assert data["total_rmb_ordenes_mes"] == 1000.0
    assert data["total_rmb_ordenes_mes"] < data["total_rmb_mes"]


def test_metricas_vendedoras_reflejan_solo_lo_realmente_pedido(
    db, client, crear_usuario, token_staff
):
    admin = crear_usuario("admin-metricas2@test.com", rol=RolUsuario.admin)
    vendedora = crear_usuario("v-metricas2@test.com", rol=RolUsuario.vendedora, nombre="Vendedora Test")
    _crear_sesion_con_pedido_parcial(db, vendedora.id)

    tok = token_staff("admin-metricas2@test.com")
    r = client.get("/api/v1/admin/metricas-vendedoras", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, r.text
    fila = next(v for v in r.json()["vendedoras"] if v["user_id"] == vendedora.id)

    assert fila["total_rmb"] == 1500.0
    assert fila["total_rmb_ordenes"] == 1000.0
    assert fila["total_usd_ordenes"] == 100.0  # 1000 RMB / 10.0 de tipo de cambio
