"""El aviso de cubicaje a la vendedora era un paso manual aparte (un panel de
chat que bodega tenía que abrir y mandar a mano): si nadie lo hacía, la
vendedora nunca se enteraba de cómo quedó el cubicaje del pedido. Ahora se
genera y se manda solo en cuanto bodega termina de revisar TODAS las
órdenes -ver generar_reporte_automatico en cubicaje_service.py."""
from app.models.cubicaje import TIPO_REPORTE, CubicajeMensaje
from app.models.item import Item
from app.models.notificacion import TIPO_CUBICAJE_BODEGA, Notificacion
from app.models.user import RolUsuario
from app.services.cubicaje_service import generar_reporte_automatico


def _sesion_con_item(crear_usuario, crear_sesion, db, *, largo, ancho, alto, ctns=1):
    vendedora = crear_usuario(f"vend-{largo}-{ancho}-{alto}@test.com", rol=RolUsuario.vendedora, nombre="Vendedora")
    sesion = crear_sesion(vendedora.id, con_item=False)
    db.add(
        Item(
            sesion_id=sesion.id,
            supplier_nombre="Prov",
            descripcion_es="Producto",
            ctns=ctns,
            qty_por_ctn=10,
            price_rmb=2.0,
            orden=1,
            largo_cm=largo,
            ancho_cm=ancho,
            alto_cm=alto,
        )
    )
    db.commit()
    db.refresh(sesion)
    return sesion, vendedora


def test_ajustado_genera_reporte_sin_detalle_de_sobrante(db, crear_usuario, crear_sesion):
    bodega = crear_usuario("bodega1@test.com", rol=RolUsuario.bodega, nombre="Bodega Uno")
    sesion, vendedora = _sesion_con_item(crear_usuario, crear_sesion, db, largo=100, ancho=100, alto=7000)

    mensaje = generar_reporte_automatico(db, sesion, "YUDA-001", bodega.id)
    db.commit()

    assert mensaje is not None
    assert mensaje.tipo == TIPO_REPORTE
    assert mensaje.resultado == "ajustado"
    assert mensaje.cbm_calculado == 70.0
    assert mensaje.referencia is None
    assert mensaje.espacio_restante_cbm is None

    avisos = db.query(Notificacion).filter(
        Notificacion.usuario_id == vendedora.id, Notificacion.tipo == TIPO_CUBICAJE_BODEGA
    ).all()
    assert len(avisos) == 1


def test_falta_calcula_espacio_restante(db, crear_usuario, crear_sesion):
    bodega = crear_usuario("bodega2@test.com", rol=RolUsuario.bodega, nombre="Bodega Dos")
    sesion, _vendedora = _sesion_con_item(crear_usuario, crear_sesion, db, largo=100, ancho=100, alto=5000)

    mensaje = generar_reporte_automatico(db, sesion, "YUDA-002", bodega.id)
    db.commit()

    assert mensaje.resultado == "falta"
    assert mensaje.cbm_calculado == 50.0
    assert mensaje.espacio_restante_cbm == 22.0


def test_sobra_avisa_sin_inventar_que_producto_se_deja_afuera(db, crear_usuario, crear_sesion):
    bodega = crear_usuario("bodega3@test.com", rol=RolUsuario.bodega, nombre="Bodega Tres")
    sesion, _vendedora = _sesion_con_item(crear_usuario, crear_sesion, db, largo=100, ancho=100, alto=8000)

    mensaje = generar_reporte_automatico(db, sesion, "YUDA-003", bodega.id)
    db.commit()

    assert mensaje.resultado == "sobra"
    assert mensaje.cbm_calculado == 80.0
    # A propósito: bodega todavía no ha dicho qué se deja afuera, así que no
    # se inventa ninguna referencia ni cantidad de cajas.
    assert mensaje.referencia is None
    assert mensaje.cajas_afectadas is None


def test_no_duplica_si_ya_existe_un_reporte(db, crear_usuario, crear_sesion):
    bodega = crear_usuario("bodega4@test.com", rol=RolUsuario.bodega, nombre="Bodega Cuatro")
    sesion, _vendedora = _sesion_con_item(crear_usuario, crear_sesion, db, largo=100, ancho=100, alto=7000)

    primero = generar_reporte_automatico(db, sesion, "YUDA-004", bodega.id)
    db.commit()
    assert primero is not None

    segundo = generar_reporte_automatico(db, sesion, "YUDA-004", bodega.id)
    db.commit()
    assert segundo is None

    total = db.query(CubicajeMensaje).filter(CubicajeMensaje.sesion_id == sesion.id).count()
    assert total == 1
