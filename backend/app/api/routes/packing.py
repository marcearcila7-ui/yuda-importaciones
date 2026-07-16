import asyncio
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.imagen_valida import detectar_tipo_imagen
from app.database import get_db
from app.models.cliente import Cliente
from app.models.item import Item
from app.models.pedido import PedidoGenerado
from app.models.seguimiento import SeguimientoPedido
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.cotizacion import CotizacionRequest
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
from app.services.excel_service import generar_packing_list_excel
from app.services.packing_service import calcular_campos_item
from app.services.pdf_service import generar_packing_list_pdf
from app.services.storage_service import subir_foto

# El router se monta en main.py con prefijo /api/v1 (sin prefijo propio aquí)
router = APIRouter(tags=["packing"])

# Tipos de imagen permitidos para la foto final del producto
_TIPOS_FOTO = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_MAX_FOTO_BYTES = 25 * 1024 * 1024


def _exigir_roles(usuario: User, *roles: str) -> None:
    """Lanza 403 si el rol del usuario no está entre los permitidos"""
    if usuario.rol.value not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para esta acción",
        )


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
        orden=item.orden,
        **calculados,
    )


def _obtener_sesion(db: Session, sesion_id: str) -> Sesion:
    """Devuelve la sesión o lanza 404"""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesión no encontrada",
        )
    return sesion


# ──────────────── SESIONES ────────────────


@router.get("/sesiones", response_model=list[SesionResponse])
def listar_sesiones(
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Sesion]:
    """Lista sesiones: admin/contadora ven todas, vendedora solo las propias"""
    query = db.query(Sesion)
    if usuario.rol.value == "vendedora":
        query = query.filter(Sesion.user_id == usuario.id)
    return query.order_by(Sesion.created_at.desc()).all()


@router.post("/sesiones", response_model=SesionResponse, status_code=status.HTTP_201_CREATED)
def crear_sesion(
    datos: SesionCreate,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Sesion:
    """Crea una sesión asociada al usuario actual (solo admin y vendedora)"""
    _exigir_roles(usuario, "admin", "vendedora")

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
    _exigir_roles(usuario, "admin")
    _obtener_sesion(db, sesion_id)

    # Borrar primero los registros que dependen de la sesión (FK)
    db.query(Item).filter(Item.sesion_id == sesion_id).delete()
    db.query(PedidoGenerado).filter(PedidoGenerado.sesion_id == sesion_id).delete()
    db.query(SeguimientoPedido).filter(SeguimientoPedido.sesion_id == sesion_id).delete()
    db.query(Sesion).filter(Sesion.id == sesion_id).delete()
    db.commit()
    return {"detail": "Cotización eliminada"}


# ──────────────── ÍTEMS ────────────────


@router.get("/sesiones/{sesion_id}/items", response_model=list[ItemResponse])
def listar_items(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItemResponse]:
    """Lista los ítems de una sesión con sus campos calculados"""
    sesion = _obtener_sesion(db, sesion_id)
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
    _exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id)

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
    _exigir_roles(usuario, "admin", "vendedora")
    _obtener_sesion(db, sesion_id)

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
    _exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id)

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
    _exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id)

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
    _exigir_roles(usuario, "admin")

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
    sesion = _obtener_sesion(db, sesion_id)
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
    sesion = _obtener_sesion(db, sesion_id)
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
    sesion = _obtener_sesion(db, sesion_id)
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
    sesion = _obtener_sesion(db, sesion_id)
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
