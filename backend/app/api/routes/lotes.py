import asyncio
import uuid

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import exigir_acceso_sesion, get_current_user, require_roles
from app.core.config import settings
from app.core.imagen_valida import detectar_tipo_imagen
from app.database import get_db
from app.models.lote import LoteItem, LoteOCR
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.lote import LoteActivo, LoteCreado, LoteEstado, LoteItemInfo
from app.schemas.packing import RecorteRequest
from app.services.lote_service import ocr_de_bytes, ocr_de_url, procesar_lote
from app.services.imagen_service import convertir_a_jpeg
from app.services.recorte_service import recortar_producto, recuadro_valido
from app.services.storage_service import subir_foto

router = APIRouter(tags=["lotes"])

TIPOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    # Las fotos de iPhone son HEIC. Se aceptan y se convierten a JPEG al entrar.
    "image/heic": ".heic",
}

# Lo que un iPhone o un navegador pueden declarar para una foto HEIC.
_DECLARADOS_HEIC = {"image/heic", "image/heif", "image/heic-sequence", "image/heif-sequence"}
MAX_BYTES = 25 * 1024 * 1024

# Fotos de detalle propias de un bolso ("interior"/"herrajes"/"riata"/
# "exterior"), más 3 fotos genéricas ("extra1/2/3") para cualquier producto:
# el cliente a veces pide más ángulos además de la foto con el cartel del OCR.
TIPOS_FOTO_EXTRA = {"interior", "herrajes", "riata", "exterior", "extra1", "extra2", "extra3"}


def _verificar_dueno(db: Session, sesion_id: str, usuario: User) -> None:
    """Una vendedora solo puede operar sobre cotizaciones propias o de un
    cliente que Marcela le haya compartido (ver `exigir_acceso_sesion`);
    admin y contadora, sobre cualquiera."""
    if usuario.rol.value != "vendedora":
        return
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos sobre esta cotización",
        )
    exigir_acceso_sesion(db, sesion, usuario)


def _obtener_lote(db: Session, lote_id: str, usuario: User) -> LoteOCR:
    lote = db.query(LoteOCR).filter(LoteOCR.id == lote_id).first()
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    _verificar_dueno(db, lote.sesion_id, usuario)
    return lote


def _tipo_cotizacion(db: Session, lote: LoteOCR) -> str:
    """Le dice al OCR si esta sesión es de bolsos (para leer también esos campos)."""
    sesion = db.query(Sesion).filter(Sesion.id == lote.sesion_id).first()
    return sesion.tipo_cotizacion if sesion else "productos"


@router.post("/sesiones/{sesion_id}/lotes", response_model=LoteCreado, status_code=status.HTTP_201_CREATED)
def crear_lote(
    sesion_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> LoteCreado:
    """Crea un lote vacío para ir cargando fotos"""
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesión no encontrada")
    _verificar_dueno(db, sesion_id, usuario)
    lote = LoteOCR(sesion_id=sesion_id, estado="cargando")
    db.add(lote)
    db.commit()
    db.refresh(lote)
    return LoteCreado(lote_id=lote.id)


@router.post("/lotes/{lote_id}/foto")
async def subir_foto_lote(
    lote_id: str,
    foto: UploadFile,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube una foto al lote (la guarda en Supabase y la deja pendiente de OCR)"""
    _obtener_lote(db, lote_id, usuario)

    if foto.content_type not in TIPOS_PERMITIDOS and foto.content_type not in _DECLARADOS_HEIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten imágenes JPG, PNG o WEBP",
        )
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no debe superar 25MB",
        )
    # Validar el contenido REAL (magic bytes), no solo el content-type declarado
    tipo_real = detectar_tipo_imagen(imagen_bytes)
    if tipo_real not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen JPG, PNG o WEBP válida",
        )

    # El resto del sistema (navegador, Excel, API de vision) no entiende HEIC:
    # se convierte una sola vez, aca, y de ahi en adelante es un JPEG normal.
    if tipo_real == "image/heic":
        convertida = convertir_a_jpeg(imagen_bytes)
        if convertida is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo leer la foto del iPhone. Vuelve a intentarlo.",
            )
        imagen_bytes = convertida
        tipo_real = "image/jpeg"

    extension = TIPOS_PERMITIDOS[tipo_real]
    nombre_archivo = f"{uuid.uuid4()}{extension}"

    loop = asyncio.get_event_loop()
    foto_url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    item = LoteItem(lote_id=lote_id, foto_url=foto_url, estado="pendiente")
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"item_id": item.id}


@router.post("/lotes/{lote_id}/procesar")
def procesar(
    lote_id: str,
    background: BackgroundTasks,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Dispara el OCR del lote: lo encola para el worker, o lo corre en segundo plano"""
    lote = _obtener_lote(db, lote_id, usuario)
    if settings.USE_WORKER:
        # La cola vive en la base; el worker aparte lo toma y procesa.
        lote.estado = "encolado"
        db.commit()
        return {"detail": "Lote en cola"}
    lote.estado = "procesando"
    db.commit()
    background.add_task(procesar_lote, lote_id)
    return {"detail": "Lote en proceso"}


@router.post("/lotes/{lote_id}/reprocesar")
def reprocesar(
    lote_id: str,
    background: BackgroundTasks,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Vuelve a procesar solo las fotos que habían fallado"""
    lote = _obtener_lote(db, lote_id, usuario)
    db.query(LoteItem).filter(
        LoteItem.lote_id == lote_id, LoteItem.estado == "error"
    ).update({LoteItem.estado: "pendiente"})
    if settings.USE_WORKER:
        lote.estado = "encolado"
        db.commit()
        return {"detail": "Reprocesando (en cola)"}
    lote.estado = "procesando"
    db.commit()
    background.add_task(procesar_lote, lote_id)
    return {"detail": "Reprocesando"}


def _obtener_item(db: Session, lote_id: str, item_id: str) -> LoteItem:
    item = (
        db.query(LoteItem)
        .filter(LoteItem.id == item_id, LoteItem.lote_id == lote_id)
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Foto no encontrada")
    return item


@router.post("/lotes/{lote_id}/items/{item_id}/reanalizar", response_model=LoteItemInfo)
async def reanalizar_item(
    lote_id: str,
    item_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> LoteItem:
    """Vuelve a correr el OCR sobre la MISMA foto de un ítem puntual (reintento con IA)"""
    lote = _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)
    fotos_extra = (item.datos or {}).get("fotos_extra")
    # Los recortes a mano de las fotos de detalle (interior/herrajes/riata/
    # exterior) no dependen de la foto principal: si no se conservan acá, un
    # simple reintento de IA los borraba en silencio.
    fotos_extra_final = (item.datos or {}).get("fotos_extra_final")
    datos, estado = await ocr_de_url(item.foto_url, _tipo_cotizacion(db, lote))
    if fotos_extra and datos is not None:
        datos["fotos_extra"] = fotos_extra
    if fotos_extra_final and datos is not None:
        datos["fotos_extra_final"] = fotos_extra_final
    item.datos = datos
    item.estado = estado
    db.commit()
    db.refresh(item)
    return item


@router.post("/lotes/{lote_id}/items/{item_id}/reemplazar", response_model=LoteItemInfo)
async def reemplazar_item(
    lote_id: str,
    item_id: str,
    foto: UploadFile,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> LoteItem:
    """Reemplaza la foto de un ítem por otra y la reanaliza al instante"""
    lote = _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)

    if foto.content_type not in TIPOS_PERMITIDOS and foto.content_type not in _DECLARADOS_HEIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten imágenes JPG, PNG o WEBP",
        )
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no debe superar 25MB",
        )
    tipo_real = detectar_tipo_imagen(imagen_bytes)
    if tipo_real not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen JPG, PNG o WEBP válida",
        )

    # El resto del sistema (navegador, Excel, API de vision) no entiende HEIC:
    # se convierte una sola vez, aca, y de ahi en adelante es un JPEG normal.
    if tipo_real == "image/heic":
        convertida = convertir_a_jpeg(imagen_bytes)
        if convertida is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo leer la foto del iPhone. Vuelve a intentarlo.",
            )
        imagen_bytes = convertida
        tipo_real = "image/jpeg"

    extension = TIPOS_PERMITIDOS[tipo_real]
    nombre_archivo = f"{uuid.uuid4()}{extension}"
    loop = asyncio.get_event_loop()
    foto_url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    fotos_extra = (item.datos or {}).get("fotos_extra")
    fotos_extra_final = (item.datos or {}).get("fotos_extra_final")
    datos, estado = await ocr_de_bytes(imagen_bytes, tipo_real, _tipo_cotizacion(db, lote))
    if fotos_extra and datos is not None:
        datos["fotos_extra"] = fotos_extra
    if fotos_extra_final and datos is not None:
        datos["fotos_extra_final"] = fotos_extra_final
    item.foto_url = foto_url
    item.datos = datos
    item.estado = estado
    db.commit()
    db.refresh(item)
    return item


@router.post("/lotes/{lote_id}/items/{item_id}/foto-extra")
async def subir_foto_extra(
    lote_id: str,
    item_id: str,
    foto: UploadFile,
    tipo: str = Form(...),
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Sube una foto de detalle del bolso (interior/herrajes/riata/exterior),
    aparte de la que ya lee el OCR. Se guarda dentro de `datos.fotos_extra`."""
    _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)

    if tipo not in TIPOS_FOTO_EXTRA:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de foto inválido")

    if foto.content_type not in TIPOS_PERMITIDOS and foto.content_type not in _DECLARADOS_HEIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten imágenes JPG, PNG o WEBP",
        )
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no debe superar 25MB",
        )
    tipo_real = detectar_tipo_imagen(imagen_bytes)
    if tipo_real not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es una imagen JPG, PNG o WEBP válida",
        )

    if tipo_real == "image/heic":
        convertida = convertir_a_jpeg(imagen_bytes)
        if convertida is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se pudo leer la foto del iPhone. Vuelve a intentarlo.",
            )
        imagen_bytes = convertida
        tipo_real = "image/jpeg"

    extension = TIPOS_PERMITIDOS[tipo_real]
    nombre_archivo = f"{uuid.uuid4()}{extension}"
    loop = asyncio.get_event_loop()
    foto_url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    datos = dict(item.datos or {})
    fotos_extra = dict(datos.get("fotos_extra") or {})
    fotos_extra[tipo] = foto_url
    datos["fotos_extra"] = fotos_extra
    # Si ya había un recorte a mano de esta foto, quedaría apuntando a un
    # encuadre de la foto VIEJA: se descarta, igual que al reemplazar en el
    # packing list (ver reemplazar_foto_extra en packing.py).
    fotos_extra_final = dict(datos.get("fotos_extra_final") or {})
    fotos_extra_final.pop(tipo, None)
    datos["fotos_extra_final"] = fotos_extra_final
    item.datos = datos
    db.commit()
    return {"tipo": tipo, "foto_url": foto_url}


@router.post("/lotes/{lote_id}/items/{item_id}/recorte", response_model=LoteItemInfo)
async def guardar_recorte_lote(
    lote_id: str,
    item_id: str,
    datos: RecorteRequest,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> LoteItem:
    """Recorta/gira a mano la foto principal de un resultado de carga masiva,
    antes de agregarlo como ítem real de la cotización.

    Mismo mecanismo que el recorte del packing list (ver guardar_recorte en
    packing.py), pero sobre un `LoteItem`: el resultado se guarda en
    `datos.foto_recorte_url`, que es lo que ya usa CargaMasiva.tsx al agregar
    el producto (`foto_final_url = datos.foto_recorte_url`).
    """
    _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)

    giro = datos.giro if datos.giro in (90, 180, 270) else 0
    item_datos = dict(item.datos or {})

    # Sin recuadro y sin giro: se descarta el recorte y vuelve la foto entera.
    if datos.recuadro is None and giro == 0:
        item_datos["foto_recorte_url"] = None
        item.datos = item_datos
        db.commit()
        db.refresh(item)
        return item

    recuadro = recuadro_valido(datos.recuadro) if datos.recuadro is not None else None
    if datos.recuadro is not None and recuadro is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El recorte no es válido")
    # Girar sin recortar trabaja sobre lo que hoy se vería en los documentos;
    # recortar de nuevo siempre parte de la foto original, para no encimar recortes.
    origen_url = item.foto_url if recuadro is not None else (item_datos.get("foto_recorte_url") or item.foto_url)

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

    # afinar=False: este recuadro lo dibujó la vendedora a mano, ya es exacto.
    recorte = recortar_producto(original, recuadro, giro, afinar=False)
    if recorte is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo recortar la foto")

    nombre_archivo = f"{uuid.uuid4()}.jpg"
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None, lambda: subir_foto(recorte, nombre_archivo, "image/jpeg")
    )

    item_datos["foto_recorte_url"] = url
    item.datos = item_datos
    db.commit()
    db.refresh(item)
    return item


@router.post(
    "/lotes/{lote_id}/items/{item_id}/fotos-extra/{tipo}/recorte",
    response_model=LoteItemInfo,
)
async def guardar_recorte_foto_extra_lote(
    lote_id: str,
    item_id: str,
    tipo: str,
    datos: RecorteRequest,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> LoteItem:
    """Recorta/gira a mano una foto de detalle (interior/herrajes/riata/exterior,
    o una genérica extra1/2/3) de un resultado de carga masiva.

    Mismo mecanismo que el de la foto principal, pero siempre parte de
    `datos.fotos_extra[tipo]` (la foto ORIGINAL tal como se subió, nunca se
    sobreescribe) y guarda el resultado en `datos.fotos_extra_final[tipo]`.
    """
    _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)
    if tipo not in TIPOS_FOTO_EXTRA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tipo de foto inválido")

    item_datos = dict(item.datos or {})
    original_url = (item_datos.get("fotos_extra") or {}).get(tipo)
    if not original_url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El producto no tiene esa foto de detalle")

    giro = datos.giro if datos.giro in (90, 180, 270) else 0

    # Sin recuadro y sin giro: se descarta el ajuste y vuelve la foto original.
    if datos.recuadro is None and giro == 0:
        fotos_extra_final = dict(item_datos.get("fotos_extra_final") or {})
        fotos_extra_final.pop(tipo, None)
        item_datos["fotos_extra_final"] = fotos_extra_final
        item.datos = item_datos
        db.commit()
        db.refresh(item)
        return item

    recuadro = recuadro_valido(datos.recuadro) if datos.recuadro is not None else None
    if datos.recuadro is not None and recuadro is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El recorte no es válido")

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

    # afinar=False: la dibujó la vendedora a mano, ya es exacta.
    recorte = recortar_producto(original, recuadro, giro, afinar=False)
    if recorte is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo recortar la foto")

    nombre_archivo = f"{uuid.uuid4()}.jpg"
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(
        None, lambda: subir_foto(recorte, nombre_archivo, "image/jpeg")
    )

    fotos_extra_final = dict(item_datos.get("fotos_extra_final") or {})
    fotos_extra_final[tipo] = url
    item_datos["fotos_extra_final"] = fotos_extra_final
    item.datos = item_datos
    db.commit()
    db.refresh(item)
    return item


@router.get("/lotes/{lote_id}", response_model=LoteEstado)
def estado_lote(
    lote_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoteEstado:
    """Devuelve el estado y los resultados del lote (para consultar el avance).

    Excluye los resultados que ya se agregaron como ítem real (item_id no
    nulo): si no, al retomar un lote interrumpido volvían a aparecer para
    revisar y "Agregar buenos" los duplicaba en la cotización.
    """
    lote = _obtener_lote(db, lote_id, usuario)
    items = (
        db.query(LoteItem)
        .filter(LoteItem.lote_id == lote_id, LoteItem.item_id.is_(None))
        .order_by(LoteItem.created_at.asc())
        .all()
    )
    procesadas = sum(1 for i in items if i.estado in ("ok", "error"))
    return LoteEstado(
        id=lote.id,
        sesion_id=lote.sesion_id,
        estado=lote.estado,
        total=len(items),
        procesadas=procesadas,
        items=items,
    )


@router.get("/sesiones/{sesion_id}/lotes/activo", response_model=LoteActivo)
def lote_activo(
    sesion_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoteActivo:
    """Devuelve el último lote de la sesión (para retomar al volver), o vacío"""
    _verificar_dueno(db, sesion_id, usuario)
    lote = (
        db.query(LoteOCR)
        .filter(LoteOCR.sesion_id == sesion_id)
        .order_by(LoteOCR.created_at.desc())
        .first()
    )
    if lote is None:
        return LoteActivo()
    return LoteActivo(lote_id=lote.id, estado=lote.estado)


@router.delete("/lotes/{lote_id}")
def borrar_lote(
    lote_id: str,
    usuario: User = Depends(require_roles("admin", "vendedora")),
    db: Session = Depends(get_db),
) -> dict:
    """Borra el lote y sus ítems (al terminar de agregar o al descartar)"""
    _obtener_lote(db, lote_id, usuario)  # 404 si no existe / 403 si no es la dueña
    db.query(LoteItem).filter(LoteItem.lote_id == lote_id).delete()
    db.query(LoteOCR).filter(LoteOCR.id == lote_id).delete()
    db.commit()
    return {"detail": "Lote eliminado"}
