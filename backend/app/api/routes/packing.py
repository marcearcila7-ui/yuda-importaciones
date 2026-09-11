import asyncio
import uuid
from datetime import datetime

import httpx

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
    RecorteRequest,
    ReordenarItem,
    SesionCreate,
    SesionResponse,
    SesionUpdate,
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
from app.services.borrado_service import (
    borrar_sesiones,
    limpiar_storage,
    tiene_movimientos_sesion,
)
from app.services.excel_service import generar_packing_list_excel
from app.services.imagen_service import convertir_a_jpeg
from app.services.packing_service import calcular_campos_item
from app.services.pdf_service import generar_packing_list_pdf
from app.services.recorte_service import recortar_producto, recuadro_valido
from app.services.traduccion_service import completar_descripciones
from app.services.storage_service import borrar_archivos, ruta_desde_url, subir_foto

# El router se monta en main.py con prefijo /api/v1 (sin prefijo propio aquí)
router = APIRouter(tags=["packing"])

# Mismas reglas de validación de fotos que en lotes.py (donde se suben por
# primera vez); se repiten acá porque son las que se usan para REEMPLAZAR la
# foto de un producto ya agregado a la cotización.
TIPOS_PERMITIDOS_FOTO = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
}
DECLARADOS_HEIC = {"image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"}
MAX_BYTES_FOTO = 25 * 1024 * 1024


async def _leer_y_validar_foto(foto: UploadFile) -> tuple[bytes, str]:
    """Lee, valida y normaliza una foto subida. Devuelve (bytes, content_type).

    Convierte HEIC (iPhone) a JPEG. Nunca deja pasar algo que no sea una
    imagen JPG/PNG/WEBP real."""
    if foto.content_type not in TIPOS_PERMITIDOS_FOTO and foto.content_type not in DECLARADOS_HEIC:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo se permiten imágenes JPG, PNG o WEBP")
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > MAX_BYTES_FOTO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La imagen no debe superar 25MB")
    tipo_real = detectar_tipo_imagen(imagen_bytes)
    if tipo_real not in TIPOS_PERMITIDOS_FOTO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El archivo no es una imagen JPG, PNG o WEBP válida")
    if tipo_real == "image/heic":
        convertida = convertir_a_jpeg(imagen_bytes)
        if convertida is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "No se pudo leer la foto del iPhone. Vuelve a intentarlo."
            )
        imagen_bytes = convertida
        tipo_real = "image/jpeg"
    return imagen_bytes, tipo_real


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
        marca=item.marca,
        fecha_recibo=item.fecha_recibo,
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
        referencia=item.referencia,
        cantidad_solicitada=item.cantidad_solicitada,
        orden=item.orden,
        colores=item.colores,
        tamano=item.tamano,
        empaque=item.empaque,
        etiqueta=item.etiqueta,
        herrajes=item.herrajes,
        riata=item.riata,
        minimo_cajas_tienda=item.minimo_cajas_tienda,
        minimo_piezas_caja_tienda=item.minimo_piezas_caja_tienda,
        fotos_extra=item.fotos_extra,
        fotos_extra_final=item.fotos_extra_final,
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
        tipo_cotizacion=datos.tipo_cotizacion,
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
    """Elimina una cotización con sus ítems, pedidos y seguimiento.

    La vendedora puede borrar las suyas; admin, cualquiera. Si ya estaba enviada,
    también desaparece del portal del cliente (el portal solo muestra las
    cotizaciones que existen). Se bloquea si tiene contabilidad registrada.
    """
    exigir_roles(usuario, "admin", "vendedora")
    _obtener_sesion(db, sesion_id, usuario)

    if tiene_movimientos_sesion(db, sesion_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Esta cotización tiene abonos o cobros registrados en la cuenta del "
                "cliente. Pide que se eliminen esos movimientos antes de borrarla."
            ),
        )

    archivos = borrar_sesiones(db, [sesion_id])
    db.commit()
    limpiar_storage(archivos)
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


@router.patch("/sesiones/{sesion_id}", response_model=SesionResponse)
def actualizar_sesion(
    sesion_id: str,
    datos: SesionUpdate,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Sesion:
    """Actualiza datos de la cotizacion. Hoy solo la marca de embarque.

    El shipping mark identifica la carga de este cliente dentro del contenedor,
    asi que es el mismo para todos sus productos y vive en la cotizacion, no en
    cada item. Solo admin y vendedora.
    """
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)
    if datos.shipping_mark is not None:
        sesion.shipping_mark = datos.shipping_mark.strip() or None
    db.commit()
    db.refresh(sesion)
    return sesion


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


@router.post("/sesiones/{sesion_id}/items/{item_id}/recorte", response_model=ItemResponse)
async def guardar_recorte(
    sesion_id: str,
    item_id: str,
    datos: RecorteRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Recorta a mano la foto de un producto, cuando el recorte automatico salio mal.

    Recibe el recuadro que dibujo la vendedora sobre la foto original y hace el
    mismo recorte que hace el OCR por su cuenta. Con `recuadro` en null se vuelve
    a la foto completa. Solo admin y vendedora.
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

    giro = datos.giro if datos.giro in (90, 180, 270) else 0

    # Sin recuadro y sin giro: se descarta el recorte y vuelve la foto entera.
    if datos.recuadro is None and giro == 0:
        item.foto_final_url = None
        db.commit()
        db.refresh(item)
        return _construir_item_response(item, sesion.tipo_cambio_usd)

    recuadro = recuadro_valido(datos.recuadro) if datos.recuadro is not None else None
    if datos.recuadro is not None and recuadro is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El recorte no es válido")
    # Girar sin recortar trabaja sobre lo que hoy sale en los documentos; recortar
    # de nuevo siempre parte de la foto original, para no encimar recortes.
    origen_url = item.foto_url if recuadro is not None else (item.foto_final_url or item.foto_url)
    if not origen_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El producto no tiene foto para recortar")

    loop = asyncio.get_event_loop()
    try:
        async with httpx.AsyncClient() as cli:
            resp = await cli.get(origen_url, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo leer la foto original")
        original = resp.content
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo leer la foto original")

    # afinar=False: este recuadro lo dibujo la vendedora a mano, ya es exacto.
    # Afinarlo (como se hace con el del modelo) podia "corregir" su selección
    # con la de otro objeto cercano en la foto — justo lo que no se quiere.
    recorte = recortar_producto(original, recuadro, giro, afinar=False)
    if recorte is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo recortar la foto")

    nombre_archivo = f"{uuid.uuid4()}.jpg"
    url = await loop.run_in_executor(
        None, lambda: subir_foto(recorte, nombre_archivo, "image/jpeg")
    )

    item.foto_final_url = url
    db.commit()
    db.refresh(item)
    return _construir_item_response(item, sesion.tipo_cambio_usd)


# Tipos válidos de foto de detalle del bolso. Mismo set que lotes.py (donde se
# suben), repetido acá para no acoplar los dos routers por un import cruzado.
TIPOS_FOTO_EXTRA = {"interior", "herrajes", "riata", "exterior"}


@router.post(
    "/sesiones/{sesion_id}/items/{item_id}/fotos-extra/{tipo}/recorte",
    response_model=ItemResponse,
)
async def guardar_recorte_foto_extra(
    sesion_id: str,
    item_id: str,
    tipo: str,
    datos: RecorteRequest,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Recorta/gira a mano una foto de detalle del bolso (interior/herrajes/riata/exterior).

    Mismo mecanismo que el recorte de la foto principal, pero siempre parte de
    `fotos_extra[tipo]` (la foto ORIGINAL tal como se subió, nunca se
    sobreescribe) y guarda el resultado en `fotos_extra_final[tipo]`. Con
    `recuadro` en null y sin giro se descarta el ajuste y vuelve la original.
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
    if tipo not in TIPOS_FOTO_EXTRA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de foto inválido")

    original_url = (item.fotos_extra or {}).get(tipo)
    if not original_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El producto no tiene esa foto de detalle")

    giro = datos.giro if datos.giro in (90, 180, 270) else 0

    # Sin recuadro y sin giro: se descarta el ajuste y vuelve la foto original.
    if datos.recuadro is None and giro == 0:
        fotos_extra_final = dict(item.fotos_extra_final or {})
        fotos_extra_final.pop(tipo, None)
        item.fotos_extra_final = fotos_extra_final
        db.commit()
        db.refresh(item)
        return _construir_item_response(item, sesion.tipo_cambio_usd)

    recuadro = recuadro_valido(datos.recuadro) if datos.recuadro is not None else None
    if datos.recuadro is not None and recuadro is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El recorte no es válido")

    loop = asyncio.get_event_loop()
    try:
        async with httpx.AsyncClient() as cli:
            resp = await cli.get(original_url, timeout=20)
        if resp.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo leer la foto original")
        original = resp.content
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "No se pudo leer la foto original")

    # afinar=False: la dibujó la vendedora a mano, ya es exacta (ver guardar_recorte).
    recorte = recortar_producto(original, recuadro, giro, afinar=False)
    if recorte is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo recortar la foto")

    nombre_archivo = f"{uuid.uuid4()}.jpg"
    url = await loop.run_in_executor(
        None, lambda: subir_foto(recorte, nombre_archivo, "image/jpeg")
    )

    fotos_extra_final = dict(item.fotos_extra_final or {})
    fotos_extra_final[tipo] = url
    item.fotos_extra_final = fotos_extra_final
    db.commit()
    db.refresh(item)
    return _construir_item_response(item, sesion.tipo_cambio_usd)


@router.post("/sesiones/{sesion_id}/items/{item_id}/foto", response_model=ItemResponse)
async def reemplazar_foto_item(
    sesion_id: str,
    item_id: str,
    foto: UploadFile,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Reemplaza la foto de un producto ya agregado a la cotización por una
    completamente distinta (al volver a editar, la vendedora puede querer
    cambiarla, no solo recortarla). Descarta cualquier recorte anterior: no
    tiene sentido sobre una foto que ya no es esa. Solo admin y vendedora."""
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.sesion_id == sesion_id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")

    imagen_bytes, tipo_real = await _leer_y_validar_foto(foto)
    extension = TIPOS_PERMITIDOS_FOTO[tipo_real]  # ya viene normalizado a jpeg/png/webp
    nombre_archivo = f"{uuid.uuid4()}{extension}"
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    item.foto_url = url
    item.foto_final_url = None
    db.commit()
    db.refresh(item)
    return _construir_item_response(item, sesion.tipo_cambio_usd)


@router.post(
    "/sesiones/{sesion_id}/items/{item_id}/fotos-extra/{tipo}/foto",
    response_model=ItemResponse,
)
async def reemplazar_foto_extra(
    sesion_id: str,
    item_id: str,
    tipo: str,
    foto: UploadFile,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemResponse:
    """Reemplaza una foto de detalle del bolso (interior/herrajes/riata/exterior)
    por una completamente distinta. Descarta cualquier recorte anterior de ese
    mismo tipo. Solo admin y vendedora."""
    exigir_roles(usuario, "admin", "vendedora")
    sesion = _obtener_sesion(db, sesion_id, usuario)
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.sesion_id == sesion_id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ítem no encontrado")
    if tipo not in TIPOS_FOTO_EXTRA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de foto inválido")

    imagen_bytes, tipo_real = await _leer_y_validar_foto(foto)
    extension = TIPOS_PERMITIDOS_FOTO[tipo_real]  # ya viene normalizado a jpeg/png/webp
    nombre_archivo = f"{uuid.uuid4()}{extension}"
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    fotos_extra = dict(item.fotos_extra or {})
    fotos_extra[tipo] = url
    item.fotos_extra = fotos_extra
    fotos_extra_final = dict(item.fotos_extra_final or {})
    fotos_extra_final.pop(tipo, None)
    item.fotos_extra_final = fotos_extra_final
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
        items, sesion.nombre_cliente, sesion.tipo_cambio_usd, sesion.tipo_cotizacion
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
        items, sesion.nombre_cliente, sesion.tipo_cambio_usd, sesion.tipo_cotizacion
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
    # La cotización del cliente lleva la descripción en los tres idiomas y el uso.
    # Lo que el OCR no alcanzó a sacar se completa acá, una sola vez por producto:
    # una celda vacía en el documento que ve el cliente no es aceptable.
    completar_descripciones(db, items)

    contenido = generar_cotizacion_excel(items, sesion, datos.idioma, sesion.tipo_cambio_usd, datos.columnas)

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
    completar_descripciones(db, items)

    contenido = generar_cotizacion_pdf(items, sesion, datos.idioma, sesion.tipo_cambio_usd, datos.columnas)

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
