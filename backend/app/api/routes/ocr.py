import asyncio
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.dependencies import get_current_user
from app.models.user import User
from app.schemas.ocr import OCRResponse, OCRResultado
from app.services.ocr_service import extraer_datos_etiqueta
from app.services.storage_service import subir_foto

router = APIRouter(prefix="/ocr", tags=["ocr"])

# Tipos de imagen permitidos y su extensión asociada
TIPOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

# Tamaño máximo permitido: 25MB (las fotos de celular suelen superar 10MB)
MAX_BYTES = 25 * 1024 * 1024


@router.post("/extraer", response_model=OCRResponse)
async def extraer(
    foto: UploadFile,
    usuario: User = Depends(get_current_user),
) -> OCRResponse:
    """Extrae datos de la etiqueta fotografiada. Solo admin y vendedora."""
    # La contadora (y cualquier otro rol) no tiene permiso
    if usuario.rol.value not in ("admin", "vendedora"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sin permisos para esta acción",
        )

    # a. Validar el tipo de archivo
    if foto.content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se permiten imágenes JPG, PNG o WEBP",
        )

    # b. Leer bytes y validar el tamaño
    imagen_bytes = await foto.read()
    if len(imagen_bytes) > MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La imagen no debe superar 25MB",
        )

    # a. Nombre único conservando la extensión original
    extension = os.path.splitext(foto.filename or "")[1]
    if not extension:
        extension = TIPOS_PERMITIDOS[foto.content_type]
    nombre_archivo = f"{uuid.uuid4()}{extension}"

    # b. Subir la imagen a Supabase Storage (storage3 es síncrono → thread aparte)
    loop = asyncio.get_event_loop()
    foto_url = await loop.run_in_executor(
        None, lambda: subir_foto(imagen_bytes, nombre_archivo, foto.content_type)
    )

    # d. Extraer datos con Claude Vision
    datos = await extraer_datos_etiqueta(imagen_bytes, foto.content_type)

    # e. Respuesta
    return OCRResponse(foto_url=foto_url, datos_extraidos=OCRResultado(**datos))
