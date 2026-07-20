import asyncio
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.core.config import settings
from app.core.imagen_valida import detectar_tipo_imagen
from app.database import get_db
from app.models.lote import LoteItem, LoteOCR
from app.models.sesion import Sesion
from app.models.user import User
from app.schemas.lote import LoteActivo, LoteCreado, LoteEstado, LoteItemInfo
from app.services.lote_service import ocr_de_bytes, ocr_de_url, procesar_lote
from app.services.storage_service import subir_foto

router = APIRouter(tags=["lotes"])

TIPOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_BYTES = 25 * 1024 * 1024


def _verificar_dueno(db: Session, sesion_id: str, usuario: User) -> None:
    """Una vendedora solo puede operar sobre cotizaciones propias (403 si no);
    admin y contadora, sobre cualquiera."""
    if usuario.rol.value != "vendedora":
        return
    sesion = db.query(Sesion).filter(Sesion.id == sesion_id).first()
    if sesion is None or sesion.user_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos sobre esta cotización",
        )


def _obtener_lote(db: Session, lote_id: str, usuario: User) -> LoteOCR:
    lote = db.query(LoteOCR).filter(LoteOCR.id == lote_id).first()
    if lote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lote no encontrado")
    _verificar_dueno(db, lote.sesion_id, usuario)
    return lote


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

    if foto.content_type not in TIPOS_PERMITIDOS:
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

    extension = os.path.splitext(foto.filename or "")[1] or TIPOS_PERMITIDOS[tipo_real]
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
    _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)
    datos, estado = await ocr_de_url(item.foto_url)
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
    _obtener_lote(db, lote_id, usuario)
    item = _obtener_item(db, lote_id, item_id)

    if foto.content_type not in TIPOS_PERMITIDOS:
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

    extension = os.path.splitext(foto.filename or "")[1] or TIPOS_PERMITIDOS[tipo_real]
    nombre_archivo = f"{uuid.uuid4()}{extension}"
    loop = asyncio.get_event_loop()
    foto_url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, tipo_real)
    )

    datos, estado = await ocr_de_bytes(imagen_bytes, tipo_real)
    item.foto_url = foto_url
    item.datos = datos
    item.estado = estado
    db.commit()
    db.refresh(item)
    return item


@router.get("/lotes/{lote_id}", response_model=LoteEstado)
def estado_lote(
    lote_id: str,
    usuario: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LoteEstado:
    """Devuelve el estado y los resultados del lote (para consultar el avance)"""
    lote = _obtener_lote(db, lote_id, usuario)
    items = (
        db.query(LoteItem)
        .filter(LoteItem.lote_id == lote_id)
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
