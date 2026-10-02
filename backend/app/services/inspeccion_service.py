"""Cotización del cliente editable por bodega: fusiona el Item original (lo
que cargó la vendedora, lo único que ve el cliente en el portal) con
ItemInspeccionBodega (lo que bodega corrigió al inspeccionar). Nunca se
escribe sobre el Item: por eso el cliente nunca ve una corrección de bodega."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.item_inspeccion import ItemInspeccionBodega
from app.models.pedido import PedidoGenerado, PedidoGeneradoItem
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.inspeccion import (
    CampoInspeccion,
    GuardarInspeccionInput,
    InspeccionItemResponse,
    InspeccionSesionResponse,
)

# (clave del schema, campo en Item, campo en ItemInspeccionBodega)
# "codigo" (item_no) ya no va: nadie lo llena y lo que de verdad se valida
# contra la caja que llega es la referencia.
# "cajas" y "marca" tampoco salen de acá: ver _item_response.
_MAPEO_CAMPOS = [
    ("referencia", "referencia", "referencia"),
    ("descripcion_es", "descripcion_es", "descripcion_es"),
    ("descripcion_en", "descripcion_en", "descripcion_en"),
    ("descripcion_zh", "descripcion_zh", "descripcion_zh"),
    ("material", "material", "material"),
    ("uso", "uso", "uso"),
    ("fecha_recibo", "fecha_recibo", "fecha_recibo"),
    ("uds_caja", "qty_por_ctn", "qty_por_ctn"),
    ("precio_rmb", "price_rmb", "price_rmb"),
    ("largo_cm", "largo_cm", "largo_cm"),
    ("ancho_cm", "ancho_cm", "ancho_cm"),
    ("alto_cm", "alto_cm", "alto_cm"),
    ("peso", "gw", "gw"),
    ("mqt", "moq_cajas", "moq_cajas"),
    ("tamano", "tamano", "tamano"),
    ("empaque", "empaque", "empaque"),
    ("etiqueta", "etiqueta", "etiqueta"),
    ("herrajes", "herrajes", "herrajes"),
    ("riata", "riata", "riata"),
    ("minimo_cajas_tienda", "minimo_cajas_tienda", "minimo_cajas_tienda"),
    ("minimo_piezas_caja_tienda", "minimo_piezas_caja_tienda", "minimo_piezas_caja_tienda"),
]


def _item_response(
    item: Item,
    insp: ItemInspeccionBodega | None,
    actualizado_por: User | None,
    cajas_pedidas: int | None = None,
    shipping_mark: str | None = None,
) -> InspeccionItemResponse:
    campos = {}
    for clave, campo_item, campo_insp in _MAPEO_CAMPOS:
        original = getattr(item, campo_item, None)
        corregido = getattr(insp, campo_insp, None) if insp else None
        campos[clave] = CampoInspeccion(original=original, corregido=corregido)

    # Las cajas contra las que bodega cuenta son las que de verdad se le
    # PIDIERON a la tienda (lo que quedó escrito en la orden), no las que se
    # cotizaron. Si el cliente pidió 3 y la cotización decía 1, a bodega le
    # tienen que llegar 3: antes mostraba 1 y la revisión se hacía contra el
    # número equivocado. `item.ctns` queda de respaldo para cotizaciones que
    # nunca generaron orden.
    campos["cajas"] = CampoInspeccion(
        original=cajas_pedidas if cajas_pedidas is not None else item.ctns,
        corregido=insp.ctns if insp else None,
    )
    # La marca es siempre la sigla del cliente, heredada de Yuda Contable; no
    # se escribe producto por producto (mismo criterio que el cotizador).
    campos["marca"] = CampoInspeccion(
        original=shipping_mark or item.marca,
        corregido=insp.marca if insp else None,
    )

    return InspeccionItemResponse(
        item_id=item.id,
        foto_url=item.foto_url,
        foto_final_url=item.foto_final_url,
        supplier_nombre=item.supplier_nombre,
        supplier_numero=item.supplier_numero,
        **campos,
        referencia_coincide=insp.referencia_coincide if insp else None,
        cajas_extra=(insp.cajas_extra if insp and insp.cajas_extra else []),
        sin_cajas_extra=insp.sin_cajas_extra if insp else False,
        debe_devolver=insp.debe_devolver if insp else False,
        no_llego=insp.no_llego if insp else False,
        fotos=(insp.fotos if insp and insp.fotos else []),
        video_url=insp.video_url if insp else None,
        actualizado_en=insp.actualizado_en if insp else None,
        actualizado_por_nombre=actualizado_por.nombre if actualizado_por else None,
    )


def _numero(sesion: Sesion) -> str:
    """Mismo formato que bodega.py: YUDA-{fecha}-{id corto}."""
    return f"YUDA-{sesion.fecha:%Y%m%d}-{sesion.id[:6].upper()}"


def construir_inspeccion_sesion(db: Session, sesion: Sesion) -> InspeccionSesionResponse:
    items = db.query(Item).filter(Item.sesion_id == sesion.id).order_by(Item.orden.asc()).all()
    item_ids = [i.id for i in items]
    inspecciones = {
        i.item_id: i
        for i in db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id.in_(item_ids)).all()
    } if item_ids else {}

    actores_ids = {i.actualizado_por_id for i in inspecciones.values() if i.actualizado_por_id}
    actores = {
        u.id: u for u in db.query(User).filter(User.id.in_(actores_ids)).all()
    } if actores_ids else {}

    vendedora = db.query(User).filter(User.id == sesion.user_id).first()
    cliente_nombre = sesion.nombre_cliente

    # Cuántas cajas se le pidieron de verdad a la tienda, por producto. Es
    # contra esto que bodega cuenta lo que llega (ver _item_response).
    cajas_pedidas: dict[str, int] = {}
    pedido_ids = [
        pid for (pid,) in db.query(PedidoGenerado.id).filter(PedidoGenerado.sesion_id == sesion.id).all()
    ]
    if pedido_ids:
        for linea in db.query(PedidoGeneradoItem).filter(
            PedidoGeneradoItem.pedido_generado_id.in_(pedido_ids)
        ):
            cajas_pedidas[linea.item_id] = linea.cantidad_pedida

    items_response = [
        _item_response(
            item,
            inspecciones.get(item.id),
            actores.get(inspecciones[item.id].actualizado_por_id) if item.id in inspecciones and inspecciones[item.id].actualizado_por_id else None,
            cajas_pedidas=cajas_pedidas.get(item.id),
            shipping_mark=sesion.shipping_mark,
        )
        for item in items
    ]

    return InspeccionSesionResponse(
        sesion_id=sesion.id,
        numero=_numero(sesion),
        fecha=sesion.fecha,
        tipo_cotizacion=getattr(sesion, "tipo_cotizacion", None),
        cliente_nombre=cliente_nombre,
        vendedora_nombre=vendedora.nombre if vendedora else None,
        vendedora_email=vendedora.email if vendedora else None,
        shipping_mark=CampoInspeccion(original=sesion.shipping_mark, corregido=sesion.shipping_mark_bodega),
        items=items_response,
    )


def aplicar_fecha_recibo_masiva(db: Session, sesion: Sesion, fecha_recibo: str) -> None:
    """Pone la misma fecha de recibo en TODOS los ítems de la sesión de una
    sola vez (para cuando todo el pedido llegó el mismo día). A propósito NO
    toca actualizado_en/actualizado_por_id: eso significa "bodega ya revisó
    este producto" (cantidades, medidas, fotos), y poner solo la fecha no es
    una revisión -si lo tocara, cada producto se vería con el visto bueno
    verde sin que bodega hubiera revisado nada más que la fecha."""
    items = db.query(Item).filter(Item.sesion_id == sesion.id).all()
    item_ids = [i.id for i in items]
    existentes = {
        i.item_id: i
        for i in db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id.in_(item_ids)).all()
    } if item_ids else {}

    for item in items:
        insp = existentes.get(item.id)
        if insp is None:
            insp = ItemInspeccionBodega(item_id=item.id)
            db.add(insp)
        insp.fecha_recibo = fecha_recibo

    db.commit()


def guardar_inspeccion(
    db: Session, sesion: Sesion, datos: GuardarInspeccionInput, usuario: User
) -> list[dict]:
    """Guarda las correcciones de bodega y devuelve los avisos nuevos a mandar
    por el chat de cubicaje: uno por cada producto que en ESTE guardado pasó de
    no marcado a marcado como "hay que devolver" o "no llegó" (si ya venía
    marcado de un guardado anterior, no se repite el aviso)."""
    if datos.shipping_mark is not None:
        sesion.shipping_mark_bodega = datos.shipping_mark or None

    item_ids = [d.item_id for d in datos.items]
    validos = {
        i.id for i in db.query(Item.id).filter(Item.sesion_id == sesion.id, Item.id.in_(item_ids)).all()
    }
    existentes = {
        i.item_id: i
        for i in db.query(ItemInspeccionBodega).filter(ItemInspeccionBodega.item_id.in_(item_ids)).all()
    }

    ahora = datetime.now(timezone.utc)
    avisos: list[dict] = []
    for entrada in datos.items:
        if entrada.item_id not in validos:
            continue
        insp = existentes.get(entrada.item_id)
        if insp is None:
            insp = ItemInspeccionBodega(item_id=entrada.item_id)
            db.add(insp)
            existentes[entrada.item_id] = insp

        devolver_antes = insp.debe_devolver
        no_llego_antes = insp.no_llego

        for clave, _campo_item, campo_insp in _MAPEO_CAMPOS:
            setattr(insp, campo_insp, getattr(entrada, clave))
        insp.referencia_coincide = entrada.referencia_coincide
        insp.cajas_extra = (
            [c.model_dump() for c in entrada.cajas_extra] if entrada.cajas_extra else None
        )
        insp.sin_cajas_extra = entrada.sin_cajas_extra
        insp.debe_devolver = entrada.debe_devolver
        insp.no_llego = entrada.no_llego
        insp.actualizado_en = ahora
        insp.actualizado_por_id = usuario.id

        referencia = entrada.referencia or entrada.codigo or entrada.item_id
        descripcion = entrada.descripcion_es or entrada.descripcion_en or referencia
        if entrada.debe_devolver and not devolver_antes:
            avisos.append({"tipo": "devolver", "referencia": referencia, "descripcion": descripcion})
        if entrada.no_llego and not no_llego_antes:
            avisos.append({"tipo": "no_llego", "referencia": referencia, "descripcion": descripcion})

    db.commit()
    return avisos
