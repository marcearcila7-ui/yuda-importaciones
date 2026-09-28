"""bodega-resumen debe mostrar mensajes de cubicaje sin leer por cotización
(para que una vendedora con varios clientes activos a la vez vea de un
vistazo dónde hay algo nuevo) y subir arriba las que tienen mensajes nuevos."""
from datetime import datetime, timedelta, timezone

from app.models.cubicaje import CubicajeMensaje, CubicajeVisto
from app.models.seguimiento import SeguimientoPedido
from app.models.user import RolUsuario


def _sesion_en_bodega(db, crear_sesion, vendedora_id, cliente_id, updated_at):
    sesion = crear_sesion(vendedora_id, cliente_id, con_item=True)
    db.add(SeguimientoPedido(sesion_id=sesion.id, estado="proveedor_recibio", updated_at=updated_at))
    db.commit()
    return sesion


def test_cuenta_no_leidos_y_arma_preview(db, client, crear_usuario, crear_cliente, crear_sesion, token_staff):
    vendedora = crear_usuario("cub1@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("cubbodega1@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("cubcliente1@test.com", vendedora.id)
    ahora = datetime.now(timezone.utc)
    sesion = _sesion_en_bodega(db, crear_sesion, vendedora.id, cliente.id, ahora)

    # Un mensaje de bodega (cuenta como no leído) y uno de la propia vendedora
    # (no debe contar para ella misma).
    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo="nota", autor_id=bodega.id, mensaje="¿Cuántas cajas van?"))
    db.commit()
    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo="respuesta", autor_id=vendedora.id, mensaje="20 cajas"))
    db.commit()

    token = token_staff("cub1@test.com")
    r = client.get("/api/v1/pedidos/bodega-resumen", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    fila = next(f for f in r.json() if f["sesion_id"] == sesion.id)
    assert fila["cubicaje_mensajes_sin_leer"] == 1
    assert fila["cubicaje_ultimo_mensaje"] == "20 cajas"


def test_visto_descuenta_mensajes_ya_leidos(db, client, crear_usuario, crear_cliente, crear_sesion, token_staff):
    vendedora = crear_usuario("cub2@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("cubbodega2@test.com", rol=RolUsuario.bodega)
    cliente = crear_cliente("cubcliente2@test.com", vendedora.id)
    ahora = datetime.now(timezone.utc)
    sesion = _sesion_en_bodega(db, crear_sesion, vendedora.id, cliente.id, ahora)

    antes = ahora - timedelta(minutes=10)
    db.add(
        CubicajeMensaje(
            sesion_id=sesion.id, tipo="nota", autor_id=bodega.id, mensaje="mensaje viejo", created_at=antes
        )
    )
    db.commit()
    # La vendedora vio el chat justo después de ese mensaje viejo.
    db.add(CubicajeVisto(sesion_id=sesion.id, usuario_id=vendedora.id, visto_en=ahora - timedelta(minutes=5)))
    db.commit()
    db.add(CubicajeMensaje(sesion_id=sesion.id, tipo="nota", autor_id=bodega.id, mensaje="mensaje nuevo"))
    db.commit()

    token = token_staff("cub2@test.com")
    r = client.get("/api/v1/pedidos/bodega-resumen", headers={"Authorization": f"Bearer {token}"})
    fila = next(f for f in r.json() if f["sesion_id"] == sesion.id)
    assert fila["cubicaje_mensajes_sin_leer"] == 1
    assert fila["cubicaje_ultimo_mensaje"] == "mensaje nuevo"


def test_las_que_tienen_mensajes_nuevos_suben_arriba(
    db, client, crear_usuario, crear_cliente, crear_sesion, token_staff
):
    vendedora = crear_usuario("cub3@test.com", rol=RolUsuario.vendedora)
    bodega = crear_usuario("cubbodega3@test.com", rol=RolUsuario.bodega)
    cliente_a = crear_cliente("cubclientea@test.com", vendedora.id, nombre="Cliente A")
    cliente_b = crear_cliente("cubclienteb@test.com", vendedora.id, nombre="Cliente B")
    ahora = datetime.now(timezone.utc)

    # A es la más reciente por actividad, pero sin mensajes nuevos.
    sesion_a = _sesion_en_bodega(db, crear_sesion, vendedora.id, cliente_a.id, ahora)
    # B es más vieja por actividad, pero SÍ tiene un mensaje de bodega sin leer.
    sesion_b = _sesion_en_bodega(db, crear_sesion, vendedora.id, cliente_b.id, ahora - timedelta(hours=1))
    db.add(CubicajeMensaje(sesion_id=sesion_b.id, tipo="nota", autor_id=bodega.id, mensaje="urgente"))
    db.commit()

    token = token_staff("cub3@test.com")
    r = client.get("/api/v1/pedidos/bodega-resumen", headers={"Authorization": f"Bearer {token}"})
    ids_en_orden = [f["sesion_id"] for f in r.json()]
    assert ids_en_orden.index(sesion_b.id) < ids_en_orden.index(sesion_a.id)
