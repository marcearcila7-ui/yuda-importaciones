"""Cotización del cliente editable por bodega: fusiona el Item original (lo
que cargó la vendedora, lo único que ve el cliente en el portal) con
ItemInspeccionBodega (lo que bodega corrigió al inspeccionar). Nunca se
escribe sobre el Item: por eso el cliente nunca ve una corrección de bodega."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.item_inspeccion import ItemInspeccionBodega
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.inspeccion import (
    CampoInspeccion,
    GuardarInspeccionInput,
    InspeccionItemResponse,
    InspeccionSesionResponse,
)

# (clave del schema, campo en Item, campo en ItemInspeccionBodega)
_MAPEO_CAMPOS = [
    ("referencia", "referencia", "referencia"),
    ("codigo", "item_no", "item_no"),
    ("descripcion_es", "descripcion_es", "descripcion_es"),
    ("descripcion_en", "descripcion_en", "descripcion_en"),
    ("descripcion_zh", "descripcion_zh", "descripcion_zh"),
    ("material", "material", "material"),
    ("uso", "uso", "uso"),
    ("marca", "marca", "marca"),
    ("fecha_recibo", "fecha_recibo", "fecha_recibo"),
    ("cajas", "ctns", "ctns"),
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


def _item_response(item: Item, insp: ItemInspeccionBodega | None, actualizado_por: User | None) -> InspeccionItemResponse:
    campos = {}
    for clave, campo_item, campo_insp in _MAPEO_CAMPOS:
        original = getattr(item, campo_item, None)
        corregido = getattr(insp, campo_insp, None) if insp else None
        campos[clave] = CampoInspeccion(original=original, corregido=corregido)

    return InspeccionItemResponse(
        item_id=item.id,
        foto_url=item.foto_url,
        foto_final_url=item.foto_final_url,
        **campos,
        referencia_coincide=insp.referencia_coincide if insp else None,
        cajas_extra=(insp.cajas_extra if insp and insp.cajas_extra else []),
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

    items_response = [
        _item_response(item, inspecciones.get(item.id), actores.get(inspecciones[item.id].actualizado_por_id) if item.id in inspecciones and inspecciones[item.id].actualizado_por_id else None)
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


def guardar_inspeccion(db: Session, sesion: Sesion, datos: GuardarInspeccionInput, usuario: User) -> None:
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
    for entrada in datos.items:
        if entrada.item_id not in validos:
            continue
        insp = existentes.get(entrada.item_id)
        if insp is None:
            insp = ItemInspeccionBodega(item_id=entrada.item_id)
            db.add(insp)
            existentes[entrada.item_id] = insp

        for clave, _campo_item, campo_insp in _MAPEO_CAMPOS:
            setattr(insp, campo_insp, getattr(entrada, clave))
        insp.referencia_coincide = entrada.referencia_coincide
        insp.cajas_extra = (
            [c.model_dump() for c in entrada.cajas_extra] if entrada.cajas_extra else None
        )
        insp.actualizado_en = ahora
        insp.actualizado_por_id = usuario.id

    db.commit()
