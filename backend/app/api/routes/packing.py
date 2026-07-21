import asyncio
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_roles, get_current_user
from app.core.imagen_valida import detectar_tipo_imagen
from app.database import get_db
from app.models.cliente import Cliente
from app.models.contenedor import Contenedor
from app.models.item import Item
from app.models.lote import LoteItem, LoteOCR
from app.models.notificacion import Notificacion
from app.models.pedido import PedidoGenerado
from app.models.seguimiento import SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.cotizacion import CotizacionRequest
from app.schemas.factura import FacturaRequest
from app.schemas.packing import (
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    ReordenarItem,
    SesionCreate,
    SesionResponse,
)
from app.services.cotizacion_service import (
    generar_cotizacion_excel,
    generar_cotizacion_pdf,
)
from app.services.factura_service import (
    generar_factura_excel,
    generar_factura_pdf,
    numero_factura,
)
from app.services.excel_service import generar_packing_list_excel
from app.services.packing_service import calcular_campos_item
from app.services.pdf_service import generar_packing_list_pdf
from app.services.storage_service import borrar_archivos, ruta_desde_url, subir_foto

# El router se monta en main.py con prefijo /api/v1 (sin prefijo propio aquí)
router = APIRouter(tags=["packing"])

# Tipos de imagen permitidos para la foto final del producto
_TIPOS_FOTO = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_MAX_FOTO_BYTES = 25 * 1024 * 1024


def _construir_item_response(item: Item, tipo_cambio_usd: float) -> ItemResponse:
    """Arma un ItemResponse combinando los campos crudos con los calculados"""
    calculados = calcular_campos_item(item, tipo_cambio_usd)
    return ItemResponse(
        id=item.id,
        sesion_id=item.sesion_id,
        foto_url=item.foto_url,
        foto_final_url=item.foto_final_url,
        supplier_nombre=item.supplier_nombre,
        supplier_numero=item.supplier_numero,
        item_no=item.item_no,
        descripcion_es=item.descripcion_es,
        descripcion_en=item.descripcion_en,
        descripcion_zh=item.descripcion_zh,
        material=item.material,
        uso=item.uso,
        qty_por_ctn=item.qty_por_ctn,
        price_rmb=item.price_rmb,
        gw=item.gw,
        largo_cm=item.largo_cm,
        ancho_cm=item.ancho_cm,
        alto_cm=item.alto_cm,
        moq_cajas=item.moq_cajas,
        ctns=item.ctns,
        cantidad_solicitada=item.cantidad_solicitada,
        orden=item.orden,
        **calculados,
    )


def _obtener_sesion(db: Session, sesion_id: str, usuario: User) -> Sesion:
    """Devuelve la sesión o lanza 404. Una vendedora solo puede acceder a las
    suyas (403 en caso contrario); admin y contadora ven todas."""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    if usuario.rol.value == "vendedora" and sesion.user_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos sobre esta cotización",
        )
    return sesion


# ──────────────── SESIONES ────────────────


@router.get("/sesiones", response_model=list[SesionResponse])
def listar_sesiones(
    # Paginación opcional: sin `limit` devuelve todo (comportamiento anterior).
    limit: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Sesion]:
    """Lista sesiones: admin/contadora ven todas, vendedora solo las propias"""
    query = db.query(Sesion)
    if usuario.rol.value == "vendedora":
        query = query.filter(Sesion.user_id == usuario.id)
    query = query.order_by(Sesion.created_at.desc())
    if limit is not None:
        query = query.limit(limit).offset(offset)
    return query.all()


@router.post("/sesiones", response_model=SesionResponse, status_code=status.HTTP_201_CREATED)
def crear_sesion(
    datos: SesionCreate,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Sesion:
    """Crea una sesión asociada al usuario actual (solo admin y vendedora)"""
    exigir_roles(usuario, "admin", "vendedora")

    nombre = datos.nombre_cliente
    # Si se crea para un cliente del portal, validar y usar su nombre
    if datos.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == datos.cliente_id).first()
        if cliente is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Cliente no encontrado")
        if usuario.rol.value == "vendedora" and cliente.vendedora_id != usuario.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Sin permisos sobre este cliente")
        nombre = cliente.nombre

    sesion = Sesion(
        nombre_cliente=nombre,
        fecha=datetime.now().date(),
        tipo_cambio_usd=datos.tipo_cambio_usd,
        user_id=usuario.id,
        cliente_id=datos.cliente_id,
    )
    db.add(sesion)
    db.commit()
    db.refresh(sesion)
    return sesion


@router.delete("/sesiones/{sesion_id}")
def eliminar_sesion(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Elimina una cotización con sus ítems y pedidos (solo admin)"""
    exigir_roles(usuario, "admin")
    _obtener_sesion(db, sesion_id, usuario)

    # Recolectar las URLs de archivos para borrarlos del storage tras el commit.
    lote_ids = [
        lid for (lid,) in db.query(LoteOCR.id).filter(LoteOCR.sesion_id == sesion_id).all()
    ]
    fotos_urls: list[str | None] = []
    for foto_url, foto_final in db.query(Item.foto_url, Item.foto_final_url).filter(
        Item.sesion_id == sesion_id
    ):
        fotos_urls.extend([foto_url, foto_final])
    if lote_ids:
        fotos_urls.extend(
            u for (u,) in db.query(LoteItem.foto_url).filter(LoteItem.lote_id.in_(lote_ids))
        )
    pedidos_urls: list[str | None] = []
    for xlsx, pdf in db.query(PedidoGenerado.archivo_xlsx_url, PedidoGenerado.archivo_pdf_url).filter(
        PedidoGenerado.sesion_id == sesion_id
    ):
        pedidos_urls.extend([xlsx, pdf])

    # Borrar primero los registros que dependen de la sesión (FK)
    db.query(Item).filter(Item.sesion_id == sesion_id).delete()
    db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion_id).delete()
    db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).delete()
    # Avisos internos que referencian esta cotización (FK notificaciones.sesion_id)
    db.query(Notificacion).filter(Notificacion.sesion_id == sesion_id).delete()
    # Lotes de OCR (carga masiva): primero las fotos (LoteItem) y luego los lotes,
    # respetando las FK lote_items.lote_id -> lotes_ocr.id -> sesiones.id
    if lote_ids:
        db.query(LoteItem).filter(LoteItem.lote_id.in_(lote_ids)).delete(synchronize_session=False)
        db.query(LoteOCR).filter(LoteOCR.sesion_id == sesion_id).delete(synchronize_session=False)
    db.query(Sesion).filter(Sesion.id == sesion_id).delete()
    db.commit()

    # Limpieza best-effort del storage (no bloquea si falla): fotos y pedidos.
    borrar_archivos("fotos", [ruta_desde_url(u, "fotos") for u in fotos_urls])
    borrar_archivos("pedidos", [ruta_desde_url(u, "pedidos") for u in pedidos_urls])
    return {"detail": "Cotización eliminada"}


# ──────────────── ÍTEMS ────────────────


@router.get("/sesiones/{sesion_id}/items", response_model=list[ItemResponse])
def listar_items(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItemResponse]:
    """Lista los ítems de una sesión con sus campos calculados"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )
    return [_construir_item_response(item, sesion.tipo_cambio_usd) for item in items]


@router.post(
    "/sesiones/{sesion_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_item(
    sesion_id: str,
    datos: ItemCreate,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Agrega un ítem a la sesión (solo admin y vendedora)"""
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)

    # orden = máximo actual + 1; si no hay ítems, 1
    max_orden = (
        db.query(Item.orden)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.desc())
        .first()
    )
    nuevo_orden = (max_orden[0] + 1) if max_orden else 1

    payload = datos.model_dump()
    payload["orden"] = nuevo_orden
    item = Item(sesion_id=sesion_id, **payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _construir_item_response(item, sesion.tipo_cambio_usd)


@router.patch("/sesiones/{sesion_id}/items/reordenar")
def reordenar_items(
    sesion_id: str,
    nuevos_ordenes: list[ReordenarItem],
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Actualiza el campo orden de varios ítems en una sola transacción"""
    exigir_roles(usuario, "admin", "vendedora")
    _obtener_sesion(db, sesion_id, usuario)

    for entrada in nuevos_ordenes:
        db.query(Item).filter(
            Item.id == entrada.id, Item.sesion_id == sesion_id
        ).update({Item.orden: entrada.orden})
    db.commit()
    return {"detail": "Orden actualizado"}


@router.patch("/sesiones/{sesion_id}/items/{item_id}", response_model=ItemResponse)
def actualizar_item(
    sesion_id: str,
    item_id: str,
    datos: ItemUpdate,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Actualiza parcialmente un ítem (solo admin y vendedora)"""
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)

    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.sesion_id == sesion_id)
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem no encontrado",
        )

    # Solo se aplican los campos presentes en el body
    cambios = datos.model_dump(exclude_unset=True)
    for clave, valor in cambios.items():
        setattr(item, clave, valor)
    db.commit()
    db.refresh(item)
    return _construir_item_response(item, sesion.tipo_cambio_usd)


@router.post("/sesiones/{sesion_id}/items/{item_id}/foto-final", response_model=ItemResponse)
async def subir_foto_final(
    sesion_id: str,
    item_id: str,
    foto: UploadFile,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Sube/reemplaza la foto FINAL (limpia) de un producto.

    Esta foto solo se muestra en los documentos del cliente y del proveedor;
    el OCR sigue usando la foto de datos (foto_url). Solo admin y vendedora.
    """
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)

    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.sesion_id == sesion_id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")

    if foto.content_type not in _TIPOS_FOTO:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Solo se permiten imágenes JPG, PNG o WEBP"
        )
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > _MAX_FOTO_BYTES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La imagen no debe superar 25MB")
    # Validar el contenido REAL (magic bytes), no solo el content-type declarado
    tipo_real = detectar_tipo_imagen(imagen_bytes)
    if tipo_real not in _TIPOS_FOTO:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El archivo no es una imagen JPG, PNG o WEBP válida"
        )

    extension = os.path.splitext(foto.filename or "")[1] or _TIPOS_FOTO[tipo_real]
    nombre_archivo = f"{uuid.uuid4()}{extension}"
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    item.foto_final_url = url
    db.commit()
    db.refresh(item)
    return _construir_item_response(item, sesion.tipo_cambio_usd)


@router.delete("/sesiones/{sesion_id}/items/{item_id}")
def eliminar_item(
    sesion_id: str,
    item_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Elimina un ítem (solo admin)"""
    exigir_roles(usuario, "admin")

    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.sesion_id == sesion_id)
        .first()
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ítem no encontrado",
        )

    db.delete(item)
    db.commit()
    return {"detail": "Ítem eliminado"}


# ──────────────── EXPORTACIÓN ────────────────


@router.get("/sesiones/{sesion_id}/exportar/packing-excel")
def exportar_packing_excel(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Genera y descarga el Packing List en Excel"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    contenido = generar_packing_list_excel(
        items, sesion.nombre_cliente, sesion.tipo_cambio_usd
    )

    fecha = datetime.now().strftime("%Y%m%d")
    nombre_archivo = f"{fecha}_{sesion.nombre_cliente}_PackingList.xlsx"

    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/sesiones/{sesion_id}/exportar/packing-pdf")
def exportar_packing_pdf(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Genera y descarga el Packing List en PDF (con fotos)"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    contenido = generar_packing_list_pdf(
        items, sesion.nombre_cliente, sesion.tipo_cambio_usd
    )

    fecha = datetime.now().strftime("%Y%m%d")
    nombre_archivo = f"{fecha}_{sesion.nombre_cliente}_PackingList.pdf"

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.post("/sesiones/{sesion_id}/exportar/cotizacion-excel")
def exportar_cotizacion_excel(
    sesion_id: str,
    datos: CotizacionRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Genera la cotización para el cliente en Excel (multiidioma)"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    contenido = generar_cotizacion_excel(items, sesion, datos.idioma, sesion.tipo_cambio_usd)

    fecha = datetime.now().strftime("%Y%m%d")
    nombre_archivo = f"{fecha}_{sesion.nombre_cliente}_Cotizacion_{datos.idioma}.xlsx"

    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.post("/sesiones/{sesion_id}/exportar/cotizacion-pdf")
def exportar_cotizacion_pdf(
    sesion_id: str,
    datos: CotizacionRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Genera la cotización para el cliente en PDF (multiidioma)"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    contenido = generar_cotizacion_pdf(items, sesion, datos.idioma, sesion.tipo_cambio_usd)

    fecha = datetime.now().strftime("%Y%m%d")
    nombre_archivo = f"{fecha}_{sesion.nombre_cliente}_Cotizacion_{datos.idioma}.pdf"

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


def _resolver_factura(
    db: Session, sesion: Sesion, contenedor_id: str | None
) -> tuple[float, str | None]:
    """Devuelve (TRM a usar, nombre de la vendedora) para facturar.

    Si llega `contenedor_id`, vincula la cotización a ese contenedor y usa su TRM.
    Si no, usa el contenedor ya vinculado; en su defecto, `sesion.tipo_cambio_usd`.
    """
    if contenedor_id is not None:
        contenedor = db.query(Contenedor).filter(Contenedor.id == contenedor_id).first()
        if contenedor is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Contenedor no encontrado")
        sesion.contenedor_id = contenedor.id
        db.commit()
        trm = contenedor.trm_usd
    elif sesion.contenedor_id:
        contenedor = db.query(Contenedor).filter(Contenedor.id == sesion.contenedor_id).first()
        trm = contenedor.trm_usd if contenedor else sesion.tipo_cambio_usd
    else:
        trm = sesion.tipo_cambio_usd

    vendedora = db.query(User).filter(User.id == sesion.user_id).first()
    return trm, (vendedora.nombre if vendedora else None)


@router.post("/sesiones/{sesion_id}/exportar/factura-pdf")
def exportar_factura_pdf(
    sesion_id: str,
    datos: FacturaRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Genera la factura comercial en USD para el cliente (PDF)"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    trm, vendedora = _resolver_factura(db, sesion, datos.contenedor_id)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    contenido = generar_factura_pdf(items, sesion, trm, vendedora, de=datos.de, para=datos.para)
    nombre_archivo = f"{numero_factura(sesion, datetime.now())}.pdf"

    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.post("/sesiones/{sesion_id}/exportar/factura-excel")
def exportar_factura_excel(
    sesion_id: str,
    datos: FacturaRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Genera la factura comercial en USD para el cliente (Excel)"""
    sesion = _obtener_sesion(db, sesion_id, usuario)
    trm, vendedora = _resolver_factura(db, sesion, datos.contenedor_id)
    items = (
        db.query(Item)
        .filter(Item.sesion_id == sesion_id)
        .order_by(Item.orden.asc())
        .all()
    )

    contenido = generar_factura_excel(items, sesion, trm, vendedora, de=datos.de, para=datos.para)
    nombre_archivo = f"{numero_factura(sesion, datetime.now())}.xlsx"

    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )
